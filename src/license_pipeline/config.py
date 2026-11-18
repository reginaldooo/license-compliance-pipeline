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
SPIKE_MODIFIED_Z = 3.5  # Iglewicz-Hoaglin cut-off on the median-based z-score
SPIKE_MIN_MAD = 0.01  # floor of one percentage point so a flat baseline still has a scale
MAD_TO_SIGMA = 0.6745
PRICE_CHANGES = {"Microsoft": date(2026, 7, 1)}  # renewals after this date get flagged

# Fuzzy matching
FUZZY_MIN_SCORE = 88

# Injected anomalies per rule (ground truth for evaluation)
INJECT_PER_RULE = 8

# Generator extras
COMPANY_NAME = "Aerolux Group (fictional)"
SCAN_OFFSETS_DAYS = (62, 32, 2)  # monthly inventory scans, oldest first
RENEWAL_TIERS = ((30, 3, 27), (60, 33, 57), (90, 63, 87))  # (window, min, max days to notice)
N_CONTRACT_ONLY_COMBOS = 4
N_INVENTORY_ONLY_COMBOS = 4
