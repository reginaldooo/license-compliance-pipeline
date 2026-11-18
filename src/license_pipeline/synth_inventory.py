"""Synthetic inventory scans with injected over-entitlement, spikes, and orphan rows."""

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import config
from .synth_noise import UNMAPPED_NAMES, messy_name
from .synth_plan import Combo, ComboPlan

SPLIT_PROBABILITY = 0.3
MIN_SPLIT_INSTALLS = 20


def _scale(rng: np.random.Generator, value: int, lo: float, hi: float) -> int:
    return max(round(value * float(rng.uniform(lo, hi))), 1)


def _scan_totals(
    rng: np.random.Generator, entitlement: int, is_over: bool, is_spike: bool
) -> list[int]:
    """Installs per scan, oldest first. The latest scan carries the over-entitlement case."""
    if is_over:
        latest = math.ceil(entitlement * float(rng.uniform(1.1, 1.5)))
    else:
        latest = _scale(rng, entitlement, 0.5, 0.95)
    middle = _scale(rng, latest, 0.3, 0.5) if is_spike else _scale(rng, latest, 0.93, 1.0)
    oldest = _scale(rng, middle, 0.93, 1.0)
    return [oldest, middle, latest]


def _split(rng: np.random.Generator, installs: int) -> list[int]:
    if installs >= MIN_SPLIT_INSTALLS and float(rng.random()) < SPLIT_PROBABILITY:
        first = int(rng.integers(1, installs))
        return [first, installs - first]
    return [installs]


def build_inventory(
    rng: np.random.Generator,
    catalog: pd.DataFrame,
    entitlement: dict[Combo, int],
    plan: ComboPlan,
    today: date,
    n_unmapped: int = config.INJECT_PER_RULE,
) -> tuple[pd.DataFrame, list[tuple[str, str, str]]]:
    names = catalog.set_index("product_id")["catalog_name"].to_dict()
    scan_dates = [today - timedelta(days=d) for d in config.SCAN_OFFSETS_DAYS]
    rows: list[dict] = []
    truth: list[tuple[str, str, str]] = []
    inventory_only = set(plan.inventory_only)

    def add_row(scan_date: date, product_id: str | None, raw_name: str, site_id: str, n: int):
        row_id = f"I{len(rows) + 1:05d}"
        rows.append(
            {
                "row_id": row_id,
                "scan_date": scan_date,
                "raw_name": raw_name,
                "site_id": site_id,
                "installs": n,
                "_product_id": product_id,
            }
        )
        return row_id

    for combo in (*plan.normal, *plan.inventory_only):
        product_id, site_id = combo
        if combo in inventory_only:
            base = int(rng.integers(30, 200))
            totals = _scan_totals(rng, base * 2, False, False)
        else:
            totals = _scan_totals(rng, entitlement[combo], combo in plan.over, combo in plan.spike)
        for scan_date, total in zip(scan_dates, totals, strict=True):
            for part in _split(rng, total):
                name = messy_name(product_id, names[product_id], rng)
                row_id = add_row(scan_date, product_id, name, site_id, part)
                if combo in inventory_only:
                    truth.append(("dq", "inventory_without_contract", row_id))
        if combo in plan.over:
            truth.append(("alert", "installs_over_entitlement", f"{product_id}|{site_id}"))
        if combo in plan.spike:
            truth.append(("alert", "usage_spike", f"{product_id}|{site_id}"))

    site_ids = list(config.SITES)
    for _ in range(n_unmapped):
        name = UNMAPPED_NAMES[int(rng.integers(len(UNMAPPED_NAMES)))]
        site_id = site_ids[int(rng.integers(len(site_ids)))]
        row_id = add_row(scan_dates[-1], None, name, site_id, int(rng.integers(5, 61)))
        truth.append(("dq", "unmapped_product", row_id))

    return pd.DataFrame(rows), truth
