"""Synthetic usage seats and AI seats, with a fixed share of long-unused seats."""

from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import config

ACTIVE_MAX_DAYS = 80
UNUSED_MIN_DAYS = 100
UNUSED_MAX_DAYS = 400
USER_POOL = 800
AI_OVERLAP = {"P016": "P017", "P017": "P016", "P018": "P017"}


def _last_active(
    rng: np.random.Generator, n: int, today: date
) -> tuple[list[date], set[int]]:
    unused = {int(i) for i in rng.permutation(n)[: round(config.UNUSED_SEAT_SHARE * n)]}
    dates = []
    for i in range(n):
        low, high = (UNUSED_MIN_DAYS, UNUSED_MAX_DAYS) if i in unused else (0, ACTIVE_MAX_DAYS)
        dates.append(today - timedelta(days=int(rng.integers(low, high + 1))))
    return dates, unused


def build_usage(
    rng: np.random.Generator, catalog: pd.DataFrame, today: date
) -> tuple[pd.DataFrame, list[tuple[str, str, str]]]:
    eligible = catalog[(catalog["metric"] == "user") & (catalog["category"] != "ai")]
    product_ids = eligible["product_id"].tolist()
    n = config.N_USAGE_SEATS
    dates, unused = _last_active(rng, n, today)
    rows = [
        {
            "seat_id": f"SEAT-{i + 1:05d}",
            "product_id": product_ids[int(rng.integers(len(product_ids)))],
            "user_ref": f"user_{int(rng.integers(1, USER_POOL + 1)):04d}",
            "last_active_date": dates[i],
        }
        for i in range(n)
    ]
    truth = [("alert", "seat_unused_90d", rows[i]["seat_id"]) for i in sorted(unused)]
    return pd.DataFrame(rows), truth


def build_ai_seats(
    rng: np.random.Generator, catalog: pd.DataFrame, today: date
) -> tuple[pd.DataFrame, list[tuple[str, str, str]]]:
    ai = catalog[catalog["category"] == "ai"].set_index("product_id")
    product_ids = ai.index.tolist()
    n = config.N_AI_SEATS
    dates, unused = _last_active(rng, n, today)
    rows = []
    for i in range(n):
        product_id = product_ids[int(rng.integers(len(product_ids)))]
        rows.append(
            {
                "seat_id": f"AI-{i + 1:04d}",
                "product_id": product_id,
                "monthly_cost": round(int(ai.loc[product_id, "unit_cost"]) / 12, 2),
                "last_active_date": dates[i],
                "overlaps_with_product_id": AI_OVERLAP[product_id],
            }
        )
    truth = [("alert", "seat_unused_90d", rows[i]["seat_id"]) for i in sorted(unused)]
    return pd.DataFrame(rows), truth
