"""Read raw spreadsheet-style CSVs and parse their mixed date formats."""

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from . import config
from .synth_noise import MONTHS

PIPELINE_TABLES = ("owners", "contracts", "inventory", "usage", "ai_seats")
NUMERIC_COLUMNS = {
    "contracts": ("seats_purchased", "annual_cost", "notice_days"),
    "inventory": ("installs",),
    "ai_seats": ("monthly_cost",),
}
DATE_COLUMNS = {
    "contracts": ("start_date", "renewal_date"),
    "inventory": ("scan_date",),
    "usage": ("last_active_date",),
    "ai_seats": ("last_active_date",),
}
_FORMATS = ("%Y-%m-%d", "%d/%m/%Y")
_MONTH_INDEX = {name: i + 1 for i, name in enumerate(MONTHS)}


def parse_date(value: object) -> date | None:
    """Parse ISO, DD/MM/YYYY, or 'D Mon YYYY'. Anything else returns None."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    parts = text.split()
    if len(parts) == 3 and parts[1] in _MONTH_INDEX and parts[0].isdigit() and parts[2].isdigit():
        try:
            return date(int(parts[2]), _MONTH_INDEX[parts[1]], int(parts[0]))
        except ValueError:
            return None
    return None


def parse_dates(table: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    return table.assign(**{col: [parse_date(v) for v in table[col]] for col in columns})


def read_raw(raw_dir: Path = config.RAW_DIR) -> dict[str, pd.DataFrame]:
    """Read pipeline inputs as strings, keeping blanks, with numeric columns converted."""
    tables = {}
    for name in PIPELINE_TABLES:
        table = pd.read_csv(raw_dir / f"{name}.csv", dtype=str, keep_default_na=False)
        numeric = {
            col: pd.to_numeric(table[col], errors="coerce")
            for col in NUMERIC_COLUMNS.get(name, ())
        }
        tables[name] = table.assign(**numeric)
    return tables


def load_tables(raw_dir: Path = config.RAW_DIR) -> dict[str, pd.DataFrame]:
    return {
        name: parse_dates(table, DATE_COLUMNS.get(name, ()))
        for name, table in read_raw(raw_dir).items()
    }
