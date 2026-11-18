"""Alert rules. Each rule returns rows with the columns in ALERT_COLUMNS."""

from datetime import date, timedelta

import pandas as pd

from . import config

ALERT_COLUMNS = ["rule", "record_ref", "contract_id", "severity", "message"]
SEVERITY_BY_WINDOW = {30: "high", 60: "medium", 90: "low"}
MIN_COMBOS_FOR_SPIKE = 4
SITE_KEYS = ["product_id", "site_id"]


def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=ALERT_COLUMNS)


def _window_for(days_to_notice: int) -> int | None:
    return next((w for w in config.RENEWAL_WINDOWS_DAYS if days_to_notice <= w), None)


def renewal_alerts(contracts: pd.DataFrame, today: date) -> pd.DataFrame:
    """Tier by days left until the notice deadline (renewal date minus notice days)."""
    rows = []
    for c in contracts.itertuples():
        days = (c.renewal_date - today).days - int(c.notice_days)
        window = _window_for(days)
        if window is None:
            continue
        when = f"in {days} days" if days >= 0 else f"passed {-days} days ago"
        rows.append(
            {
                "rule": f"renewal_{window}",
                "record_ref": c.contract_id,
                "contract_id": c.contract_id,
                "severity": "high" if days < 0 else SEVERITY_BY_WINDOW[window],
                "message": f"Contract {c.contract_id} ({c.product_id}): notice deadline {when}, "
                f"renewal {c.renewal_date.isoformat()}",
            }
        )
    return _frame(rows)


def _scan_totals(inventory: pd.DataFrame) -> pd.DataFrame:
    """Installs per product, site, and scan date, with scan_rank 0 for the latest scan."""
    mapped = inventory.dropna(subset=["product_id"])
    totals = (
        mapped.groupby([*SITE_KEYS, "scan_date"], as_index=False)["installs"]
        .sum()
        .sort_values("scan_date")
    )
    return totals.assign(scan_rank=totals.groupby(SITE_KEYS).cumcount(ascending=False))


def installs_over_entitlement(
    contracts: pd.DataFrame, owners: pd.DataFrame, inventory: pd.DataFrame
) -> pd.DataFrame:
    sited = contracts.merge(owners[["owner_id", "site_id"]], on="owner_id")
    entitled = sited.groupby(SITE_KEYS, as_index=False)["seats_purchased"].sum()
    totals = _scan_totals(inventory)
    latest = totals[totals["scan_rank"] == 0].merge(entitled, on=SITE_KEYS)
    over = latest[latest["installs"] > latest["seats_purchased"]]
    rows = [
        {
            "rule": "installs_over_entitlement",
            "record_ref": f"{r.product_id}|{r.site_id}",
            "contract_id": None,
            "severity": "high",
            "message": f"{r.product_id} at {r.site_id}: {r.installs} installs "
            f"vs {r.seats_purchased} seats entitled",
        }
        for r in over.itertuples()
    ]
    return _frame(rows)


def unused_seats(usage: pd.DataFrame, ai_seats: pd.DataFrame, today: date) -> pd.DataFrame:
    cutoff = today - timedelta(days=config.UNUSED_DAYS)
    seats = pd.concat([usage, ai_seats], ignore_index=True)
    idle = seats[seats["last_active_date"] < cutoff]
    rows = [
        {
            "rule": "seat_unused_90d",
            "record_ref": s.seat_id,
            "contract_id": None,
            "severity": "low",
            "message": f"Seat {s.seat_id} ({s.product_id}) inactive "
            f"{(today - s.last_active_date).days} days",
        }
        for s in idle.itertuples()
    ]
    return _frame(rows)


def usage_spikes(inventory: pd.DataFrame) -> pd.DataFrame:
    """Flag product-site pairs whose install growth exceeds the IQR fence across all pairs."""
    totals = _scan_totals(inventory)
    latest = totals[totals["scan_rank"] == 0]
    previous = totals[totals["scan_rank"] == 1]
    joined = latest.merge(previous, on=SITE_KEYS, suffixes=("", "_prev"))
    joined = joined[joined["installs_prev"] > 0]
    if len(joined) < MIN_COMBOS_FOR_SPIKE:
        return _frame([])
    growth = joined["installs"] / joined["installs_prev"] - 1
    q1, q3 = growth.quantile(0.25), growth.quantile(0.75)
    fence = q3 + config.SPIKE_IQR_K * (q3 - q1)
    rows = [
        {
            "rule": "usage_spike",
            "record_ref": f"{r.product_id}|{r.site_id}",
            "contract_id": None,
            "severity": "medium",
            "message": f"{r.product_id} at {r.site_id}: installs grew {g:.0%} "
            f"({r.installs_prev} to {r.installs}), fence {fence:.0%}",
        }
        for r, g in zip(joined.itertuples(), growth, strict=True)
        if g > fence
    ]
    return _frame(rows)


def price_change_renewals(contracts: pd.DataFrame, catalog: pd.DataFrame) -> pd.DataFrame:
    """Contracts signed before a vendor price change that renew after it."""
    named = contracts.merge(catalog[["product_id", "publisher"]], on="product_id")
    rows = []
    for c in named.itertuples():
        change = config.PRICE_CHANGES.get(c.publisher)
        if change is None or not (c.start_date < change <= c.renewal_date):
            continue
        rows.append(
            {
                "rule": "price_change_renewal",
                "record_ref": c.contract_id,
                "contract_id": c.contract_id,
                "severity": "medium",
                "message": f"Contract {c.contract_id} ({c.publisher}) signed before the "
                f"{change.isoformat()} price change and renews {c.renewal_date.isoformat()}",
            }
        )
    return _frame(rows)


def run_alerts(
    contracts: pd.DataFrame,
    owners: pd.DataFrame,
    catalog: pd.DataFrame,
    inventory: pd.DataFrame,
    usage: pd.DataFrame,
    ai_seats: pd.DataFrame,
    today: date,
) -> pd.DataFrame:
    return pd.concat(
        [
            renewal_alerts(contracts, today),
            installs_over_entitlement(contracts, owners, inventory),
            unused_seats(usage, ai_seats, today),
            usage_spikes(inventory),
            price_change_renewals(contracts, catalog),
        ],
        ignore_index=True,
    )
