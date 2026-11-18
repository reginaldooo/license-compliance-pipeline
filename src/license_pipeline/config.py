"""Every tunable parameter lives here so the README assumptions register stays in sync."""

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "data" / "catalog" / "product_catalog.csv"
RAW_DIR = ROOT / "data" / "raw"
CURATED_DIR = ROOT / "data" / "curated"
REPORT_DIR = ROOT / "reports"

SEED = 42
TODAY = date(2026, 11, 18)

SITES = {"S1": ("Paris", "Europe/Paris"), "S2": ("Jakarta", "Asia/Jakarta")}

# Generator volumes
N_CONTRACTS = 120
N_OWNERS = 25
N_USAGE_SEATS = 1500
N_AI_SEATS = 200
UNUSED_SEAT_SHARE = 0.37  # research: about 36 to 38% of seats unused
UNUSED_DAYS = 90

# Alert thresholds
RENEWAL_WINDOWS_DAYS = (30, 60, 90)
SPIKE_IQR_K = 1.5
PRICE_CHANGES = {"Microsoft": date(2026, 7, 1)}  # renewals after this date get flagged

# Fuzzy matching
FUZZY_MIN_SCORE = 88

# Injected anomalies per rule (ground truth for evaluation)
INJECT_PER_RULE = 8
