import pandas as pd
import pytest

from license_pipeline import config
from license_pipeline.generate import generate_clean
from license_pipeline.normalize import match_name, normalize_inventory


@pytest.fixture(scope="module")
def catalog():
    return pd.read_csv(config.CATALOG_PATH)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Office 365 E3", "P001"),
        ("MICROSOFT 365 E3", "P001"),
        ("  Microsoft 365 E3 (x64) ", "P001"),
        ("MS Project P3", "P003"),
        ("Oracle DB EE", "P011"),
        ("Oracle Database 19c EE", "P011"),
        ("vSphere Ent Plus", "P012"),
        ("Slack BIZ+", "P015"),
        ("ChatGPT for Teams", "P018"),
        ("M365 Copilot", "P017"),
        ("Microsoft 365 Copilot", "P017"),
        ("GH Copilot Business", "P016"),
        ("Copilot Business (GitHub)", "P016"),
        ("JIRA", "P013"),
        ("Siemens NX 2306", "P010"),
    ],
)
def test_rules_map_known_aliases(catalog, raw, expected):
    product_id, method, _ = match_name(raw, catalog)
    assert (product_id, method) == (expected, "rule")


def test_fuzzy_catches_typo_the_rules_miss(catalog):
    product_id, method, score = match_name("VMwarev Sphere", catalog)
    assert (product_id, method) == ("P012", "fuzzy")
    assert score >= config.FUZZY_MIN_SCORE


@pytest.mark.parametrize("raw", ["Zorbex CAD Suite", "Legacy Reporting Tool v2", "", "   "])
def test_unknown_names_stay_unmapped(catalog, raw):
    product_id, method, _ = match_name(raw, catalog)
    assert (product_id, method) == (None, "none")


def test_normalize_inventory_adds_columns_without_mutating(catalog):
    inv = pd.DataFrame({"raw_name": ["JIRA", "JIRA", "Zorbex CAD Suite"]})
    out = normalize_inventory(inv, catalog)
    assert out["product_id"].tolist()[:2] == ["P013", "P013"]
    assert pd.isna(out["product_id"].iloc[2])
    assert out["match_method"].tolist() == ["rule", "rule", "none"]
    assert "product_id" not in inv.columns


def test_every_generated_name_maps_to_its_true_product(catalog):
    inv = generate_clean()["inventory"]
    out = normalize_inventory(inv, catalog)
    mappable = inv["_product_id"].notna()
    assert (out.loc[mappable, "product_id"] == inv.loc[mappable, "_product_id"]).all()
    assert out.loc[~mappable, "product_id"].isna().all()
