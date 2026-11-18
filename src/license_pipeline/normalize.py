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

MIN_MATCH_LEN = 6  # shorter fragments are too vague to fuzzy-match
MIN_PREFIX_LEN = 8  # a truncated cell must keep at least this much of the name
AMBIGUITY_MARGIN = 2.0  # a second product this close to the best score makes it a tie


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
    if len(text) < MIN_MATCH_LEN:
        return None, "none", 0.0
    ranked = process.extract(
        text, catalog["catalog_name"].tolist(), scorer=fuzz.WRatio,
        processor=utils.default_process, limit=2,
    )
    best = ranked[0]
    tied = len(ranked) > 1 and best[1] - ranked[1][1] <= AMBIGUITY_MARGIN
    if best[1] >= config.FUZZY_MIN_SCORE and not tied:
        return catalog["product_id"].iloc[best[2]], "fuzzy", float(best[1])
    prefixed = _unique_prefix(text, catalog)
    if prefixed is not None:
        return prefixed, "prefix", 100.0 * len(text) / len(_names_by_id(catalog)[prefixed])
    return None, "none", float(best[1])


def _names_by_id(catalog: pd.DataFrame) -> dict[str, str]:
    return dict(zip(catalog["product_id"], catalog["catalog_name"], strict=True))


def _unique_prefix(text: str, catalog: pd.DataFrame) -> str | None:
    """A cell cut off by column width: map it when it begins exactly one catalog name."""
    if len(text) < MIN_PREFIX_LEN:
        return None
    hits = [pid for pid, name in _names_by_id(catalog).items() if name.lower().startswith(text)]
    return hits[0] if len(hits) == 1 else None


def normalize_inventory(inventory: pd.DataFrame, catalog: pd.DataFrame) -> pd.DataFrame:
    """Add product_id, match_method, and match_score columns."""
    matches = {name: match_name(name, catalog) for name in inventory["raw_name"].unique()}
    resolved = [matches[name] for name in inventory["raw_name"]]
    return inventory.assign(
        product_id=[m[0] for m in resolved],
        match_method=[m[1] for m in resolved],
        match_score=[m[2] for m in resolved],
    )
