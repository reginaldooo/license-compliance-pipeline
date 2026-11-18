"""Map raw inventory names to catalog products: explicit rules first, fuzzy match second."""

import re

import pandas as pd
from rapidfuzz import fuzz, process, utils

from . import config

# Order matters: the first matching rule wins, so specific patterns come before general ones.
RULES: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern), product_id)
    for pattern, product_id in (
        (r"(github|\bgh\b).*copilot|copilot.*github", "P016"),
        (r"(m365|microsoft|365).*copilot|^microsoft copilot", "P017"),
        (r"^(m365|ms 365|office 365|microsoft 365) e3", "P001"),
        (r"visio", "P002"),
        (r"project.*(p3|plan 3)", "P003"),
        (r"acrobat", "P004"),
        (r"autocad", "P005"),
        (r"catia", "P006"),
        (r"solidworks", "P007"),
        (r"ansys", "P008"),
        (r"matlab", "P009"),
        (r"\bnx\b", "P010"),
        (r"oracle (db|database)", "P011"),
        (r"vsphere", "P012"),
        (r"\bjira\b", "P013"),
        (r"confluence", "P014"),
        (r"slack", "P015"),
        (r"chatgpt|openai", "P018"),
    )
)

NoMatch = tuple[None, str, float]


def _clean(raw: str) -> str:
    return re.sub(r"\s+", " ", raw).strip().lower()


def match_name(raw: str, catalog: pd.DataFrame) -> tuple[str | None, str, float]:
    """Return (product_id, method, score). method is rule, fuzzy, or none."""
    text = _clean(raw)
    if not text:
        return None, "none", 0.0
    for pattern, product_id in RULES:
        if pattern.search(text):
            return product_id, "rule", 100.0
    names = catalog["catalog_name"].tolist()
    best = process.extractOne(text, names, scorer=fuzz.WRatio, processor=utils.default_process)
    if best is None or best[1] < config.FUZZY_MIN_SCORE:
        return None, "none", float(best[1]) if best else 0.0
    return catalog["product_id"].iloc[best[2]], "fuzzy", float(best[1])


def normalize_inventory(inventory: pd.DataFrame, catalog: pd.DataFrame) -> pd.DataFrame:
    """Add product_id, match_method, and match_score columns."""
    matches = {name: match_name(name, catalog) for name in inventory["raw_name"].unique()}
    resolved = [matches[name] for name in inventory["raw_name"]]
    return inventory.assign(
        product_id=[m[0] for m in resolved],
        match_method=[m[1] for m in resolved],
        match_score=[m[2] for m in resolved],
    )
