from datetime import date

import pandas as pd
import pytest

from license_pipeline.generate import generate, write_raw
from license_pipeline.ingest import load_tables, parse_date, parse_dates, read_raw


@pytest.fixture(scope="module")
def raw_dir(tmp_path_factory):
    path = tmp_path_factory.mktemp("raw")
    write_raw(generate(), path)
    return path


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-11-18", date(2026, 11, 18)),
        ("18/11/2026", date(2026, 11, 18)),
        ("8 Aug 2027", date(2027, 8, 8)),
        ("08/08/2025", date(2025, 8, 8)),
        ("TBD", None),
        ("31/02/2026", None),
        ("13/13/2026", None),
        ("31 Feb 2026", None),
        ("n/a", None),
        ("", None),
        (None, None),
        (float("nan"), None),
    ],
)
def test_parse_date(text, expected):
    assert parse_date(text) == expected


def test_parse_dates_returns_new_frame():
    table = pd.DataFrame({"d": ["2026-01-02", "TBD"], "x": [1, 2]})
    out = parse_dates(table, ("d",))
    assert out["d"].tolist() == [date(2026, 1, 2), None]
    assert table["d"].tolist() == ["2026-01-02", "TBD"]


def test_read_raw_skips_ground_truth(raw_dir):
    tables = read_raw(raw_dir)
    assert set(tables) == {"owners", "contracts", "inventory", "usage", "ai_seats"}


def test_read_raw_keeps_blank_owner_and_numeric_types(raw_dir):
    contracts = read_raw(raw_dir)["contracts"]
    assert (contracts["owner_id"] == "").sum() == 8
    assert pd.api.types.is_numeric_dtype(contracts["seats_purchased"])


def test_load_tables_parses_every_date_column(raw_dir):
    tables = load_tables(raw_dir)
    renewals = tables["contracts"]["renewal_date"]
    assert renewals.isna().sum() + renewals.map(lambda d: isinstance(d, date)).sum() >= len(
        renewals
    )
    assert renewals.map(lambda d: d is None).sum() == 4
    assert tables["inventory"]["scan_date"].map(lambda d: isinstance(d, date)).all()
    assert tables["usage"]["last_active_date"].map(lambda d: isinstance(d, date)).all()
