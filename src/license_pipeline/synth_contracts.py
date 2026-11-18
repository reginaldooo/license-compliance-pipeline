"""Synthetic owners and contracts, with injected renewal, price, and data quality cases."""

from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import config
from .scenarios import Scenario
from .synth_plan import Combo, ComboPlan

FIRST = ("Camille", "Louis", "Ines", "Hugo", "Sari", "Budi", "Dewi", "Agus", "Lea", "Noah")
LAST = ("Martin", "Bernard", "Petit", "Wijaya", "Santoso", "Lambert", "Hakim", "Moreau")
NOTICE_CHOICES = (30, 60, 90)
BAD_DATES = ("TBD", "31/02/2026", "13/13/2026", "n/a")
EMAIL_DOMAIN = "aerolux.example"


def build_owners(rng: np.random.Generator) -> pd.DataFrame:
    site_ids = list(config.SITES)
    rows = []
    for i in range(config.N_OWNERS):
        first = FIRST[int(rng.integers(len(FIRST)))]
        last = LAST[int(rng.integers(len(LAST)))]
        rows.append(
            {
                "owner_id": f"O{i + 1:03d}",
                "name": f"{first} {last}",
                "site_id": site_ids[i % len(site_ids)],
                "email": f"{first}.{last}.{i + 1}@{EMAIL_DOMAIN}".lower(),
            }
        )
    return pd.DataFrame(rows)


def _base_dates(rng: np.random.Generator, publisher: str, today: date) -> tuple[date, date]:
    if publisher in config.PRICE_CHANGES:
        # one-year term started after the price change, so it is not flagged
        renewal = today + timedelta(days=int(rng.integers(230, 366)))
        return renewal - timedelta(days=365), renewal
    days = int(rng.integers(200, 901))
    term = -(-days // 365) + int(rng.integers(0, 2))
    renewal = today + timedelta(days=days)
    return renewal - timedelta(days=365 * term), renewal


def _new_contract(
    rng: np.random.Generator,
    contract_id: str,
    product: pd.Series,
    site_id: str,
    owners_by_site: dict[str, list[str]],
    today: date,
) -> dict:
    site_owners = owners_by_site[site_id]
    low, high = (50, 501) if product["metric"] == "user" else (32, 257)
    seats = int(rng.integers(low, high))
    start, renewal = _base_dates(rng, product["publisher"], today)
    return {
        "contract_id": contract_id,
        "product_id": product.name,
        "owner_id": site_owners[int(rng.integers(len(site_owners)))],
        "site_id": site_id,
        "seats_purchased": seats,
        "annual_cost": seats * int(product["unit_cost"]),
        "start_date": start,
        "renewal_date": renewal,
        "notice_days": int(NOTICE_CHOICES[int(rng.integers(len(NOTICE_CHOICES)))]),
    }


def _tier_overrides(
    rng: np.random.Generator, base: list[dict], candidates: list[int], today: date, n: int
) -> tuple[dict[int, dict], list[tuple[str, str, str]]]:
    picks = [int(i) for i in rng.permutation(candidates)[: n * len(config.RENEWAL_TIERS)]]
    overrides, truth = {}, []
    for k, (window, lo, hi) in enumerate(config.RENEWAL_TIERS):
        for idx in picks[k * n : (k + 1) * n]:
            days_to_notice = int(rng.integers(lo, hi + 1))
            renewal = today + timedelta(days=days_to_notice + base[idx]["notice_days"])
            overrides[idx] = {
                **base[idx],
                "renewal_date": renewal,
                "start_date": renewal - timedelta(days=365),
            }
            truth.append(("alert", f"renewal_{window}", base[idx]["contract_id"]))
    return overrides, truth


def _price_overrides(
    rng: np.random.Generator, base: list[dict], candidates: list[int], n: int
) -> tuple[dict[int, dict], list[tuple[str, str, str]]]:
    change = config.PRICE_CHANGES["Microsoft"]
    picks = [int(i) for i in rng.permutation(candidates)[:n]]
    overrides, truth = {}, []
    for idx in picks:
        start = change - timedelta(days=int(rng.integers(20, 301)))
        term = int(rng.integers(2, 4))
        overrides[idx] = {
            **base[idx],
            "start_date": start,
            "renewal_date": start + timedelta(days=365 * term),
        }
        truth.append(("alert", "price_change_renewal", base[idx]["contract_id"]))
    return overrides, truth


def _tier_for(days_to_notice: int) -> int | None:
    return next((w for w in (30, 60, 90) if days_to_notice <= w), None)


def _boundary_overrides(
    rng: np.random.Generator,
    base: list[dict],
    non_price: list[int],
    price: list[int],
    taken: set[int],
    today: date,
) -> tuple[dict[int, dict], list[tuple[str, str, str]]]:
    """Contracts sitting on the edges of the renewal windows and the price-change date."""
    overrides, truth = {}, []
    days = [d for d in config.BOUNDARY_NOTICE_DAYS for _ in range(config.N_PER_BOUNDARY_DAY)]
    free = [i for i in non_price if i not in taken]
    for idx, d in zip((int(i) for i in rng.permutation(free)), days, strict=False):
        renewal = today + timedelta(days=d + base[idx]["notice_days"])
        overrides[idx] = {
            **base[idx], "renewal_date": renewal, "start_date": renewal - timedelta(days=365),
        }
        tier = _tier_for(d)
        if tier:
            truth.append(("alert", f"renewal_{tier}", base[idx]["contract_id"]))
    change = config.PRICE_CHANGES["Microsoft"]
    free_ms = [i for i in price if i not in taken]
    for k, idx in enumerate(int(i) for i in rng.permutation(free_ms)[:4]):
        start = change - timedelta(days=k % 2)  # even: on the change date, odd: the day before
        overrides[idx] = {
            **base[idx], "start_date": start, "renewal_date": start + timedelta(days=730),
        }
        if k % 2:
            truth.append(("alert", "price_change_renewal", base[idx]["contract_id"]))
    return overrides, truth


def _dq_extras(
    rng: np.random.Generator, make_extra, base: list[dict], n: int
) -> tuple[list[dict], list[tuple[str, str, str]]]:
    extras, truth = [], []
    for idx in (int(i) for i in rng.permutation(len(base))[:n]):
        extras.append({**base[idx]})
        truth.append(("dq", "duplicate", base[idx]["contract_id"]))
    for _ in range(n):
        rec = {**make_extra(), "owner_id": ""}
        extras.append(rec)
        truth.append(("dq", "missing_owner", rec["contract_id"]))
    for i in range(n):
        rec = make_extra()
        if i % 2 == 0:
            rec = {**rec, "renewal_date": BAD_DATES[(i // 2) % len(BAD_DATES)]}
        else:
            rec = {**rec, "start_date": rec["renewal_date"], "renewal_date": rec["start_date"]}
        extras.append(rec)
        truth.append(("dq", "invalid_date", rec["contract_id"]))
    for _ in range(n):
        rec = make_extra()
        extras.append({**rec, "seats_purchased": -int(rec["seats_purchased"])})
        truth.append(("dq", "negative_seats", rec["contract_id"]))
    return extras, truth


def build_contracts(
    rng: np.random.Generator,
    catalog: pd.DataFrame,
    owners: pd.DataFrame,
    plan: ComboPlan,
    today: date,
    scenario: Scenario,
) -> tuple[pd.DataFrame, list[tuple[str, str, str]], dict[Combo, int]]:
    """Return contracts (with injected extras), ground-truth rows, and entitlement per combo."""
    products = catalog.set_index("product_id")
    owners_by_site = {s: g["owner_id"].tolist() for s, g in owners.groupby("site_id")}
    combos = plan.normal + plan.contract_only

    base = []
    for i in range(scenario.n_contracts):
        combo = combos[i] if i < len(combos) else combos[int(rng.integers(len(combos)))]
        base.append(
            _new_contract(
                rng, f"C{i + 1:04d}", products.loc[combo[0]], combo[1], owners_by_site, today
            )
        )

    is_price = [products.loc[c["product_id"], "publisher"] in config.PRICE_CHANGES for c in base]
    non_price = [i for i, flag in enumerate(is_price) if not flag]
    price = [i for i, flag in enumerate(is_price) if flag]
    if len(price) < scenario.n_inject:
        raise ValueError("not enough price-change publisher contracts to inject")

    tier_over, tier_truth = _tier_overrides(rng, base, non_price, today, scenario.n_inject)
    price_over, price_truth = _price_overrides(rng, base, price, scenario.n_inject)
    edge_over, edge_truth = {}, []
    if scenario.borderline:
        taken = set(tier_over) | set(price_over)
        edge_over, edge_truth = _boundary_overrides(rng, base, non_price, price, taken, today)
    records = [
        {**c, **tier_over.get(i, {}), **price_over.get(i, {}), **edge_over.get(i, {})}
        for i, c in enumerate(base)
    ]

    entitlement: dict[Combo, int] = {}
    for c in base:
        key = (c["product_id"], c["site_id"])
        entitlement[key] = entitlement.get(key, 0) + c["seats_purchased"]

    counter = [scenario.n_contracts]

    def make_extra() -> dict:
        counter[0] += 1
        combo = plan.normal[int(rng.integers(len(plan.normal)))]
        return _new_contract(
            rng, f"C{counter[0]:04d}", products.loc[combo[0]], combo[1], owners_by_site, today
        )

    extras, dq_truth = _dq_extras(rng, make_extra, records, scenario.n_inject)
    contract_only = set(plan.contract_only)
    structural = [
        ("dq", "contract_without_inventory", c["contract_id"])
        for c in records
        if (c["product_id"], c["site_id"]) in contract_only
    ]
    everything = [*records, *extras]
    order = [int(i) for i in rng.permutation(len(everything))]
    frame = pd.DataFrame([everything[i] for i in order])
    return frame, [*tier_truth, *price_truth, *edge_truth, *dq_truth, *structural], entitlement
