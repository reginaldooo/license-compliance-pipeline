"""Seeded synthetic data generator. Writes raw spreadsheet-style CSVs plus ground truth."""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .scenarios import SCENARIOS, Scenario
from .synth_contracts import build_contracts, build_owners
from .synth_inventory import build_inventory
from .synth_noise import format_date
from .synth_plan import plan_combos
from .synth_seats import build_ai_seats, build_usage

DATE_COLUMNS = {
    "contracts": ("start_date", "renewal_date"),
    "inventory": ("scan_date",),
    "usage": ("last_active_date",),
    "ai_seats": ("last_active_date",),
}
HIDDEN_COLUMNS = {"contracts": ("site_id",), "inventory": ("_product_id",)}


def generate_clean(
    seed: int = config.SEED,
    today: date = config.TODAY,
    scenario: Scenario = SCENARIOS["baseline"],
) -> dict[str, pd.DataFrame]:
    """Typed tables with true dates and hidden labels. Used by tests as an independent oracle."""
    rng = np.random.default_rng(seed)
    catalog = pd.read_csv(config.CATALOG_PATH)
    plan = plan_combos(
        rng,
        catalog["product_id"].tolist(),
        list(config.SITES),
        config.N_CONTRACT_ONLY_COMBOS,
        config.N_INVENTORY_ONLY_COMBOS,
        scenario.n_inject,
        scenario.borderline,
    )
    owners = build_owners(rng)
    contracts, contract_truth, entitlement = build_contracts(
        rng, catalog, owners, plan, today, scenario
    )
    inventory, inventory_truth = build_inventory(
        rng, catalog, entitlement, plan, today,
        scenario.n_inject * scenario.unmapped_multiplier, scenario.messy,
    )
    usage, usage_truth = build_usage(
        rng, catalog, today, scenario.n_usage_seats,
        config.IDLE_BOUNDARY_USAGE_PER_AGE if scenario.borderline else 0,
    )
    ai_seats, ai_truth = build_ai_seats(
        rng, catalog, today, scenario.n_ai_seats,
        config.IDLE_BOUNDARY_AI_PER_AGE if scenario.borderline else 0,
    )
    mappable = inventory[inventory["_product_id"].notna()]
    match_truth = [
        ("match", "name_match", f"{row}->{product}")
        for row, product in zip(mappable["row_id"], mappable["_product_id"], strict=True)
    ]
    truth = pd.DataFrame(
        [*contract_truth, *inventory_truth, *usage_truth, *ai_truth, *match_truth],
        columns=["kind", "rule", "record_ref"],
    )
    return {
        "catalog": catalog,
        "owners": owners,
        "contracts": contracts,
        "inventory": inventory,
        "usage": usage,
        "ai_seats": ai_seats,
        "ground_truth": truth,
    }


def _to_raw(
    clean: dict[str, pd.DataFrame], seed: int, extra_dates: bool = False
) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed + 1)
    raw = {}
    for name, table in clean.items():
        if name == "catalog":
            continue
        out = table.drop(columns=list(HIDDEN_COLUMNS.get(name, ())))
        for col in DATE_COLUMNS.get(name, ()):
            out = out.assign(**{col: [format_date(v, rng, extra_dates) for v in out[col]]})
        raw[name] = out
    return raw


def generate(
    seed: int = config.SEED,
    today: date = config.TODAY,
    scenario: Scenario = SCENARIOS["baseline"],
) -> dict[str, pd.DataFrame]:
    return _to_raw(generate_clean(seed, today, scenario), seed, scenario.messy)


def write_raw(raw: dict[str, pd.DataFrame], out_dir: Path = config.RAW_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, table in raw.items():
        path = out_dir / f"{name}.csv"
        table.to_csv(path, index=False)
        paths.append(path)
    return paths


def main() -> None:
    for path in write_raw(generate()):
        print(path)


if __name__ == "__main__":
    main()
