"""Data scenarios of increasing difficulty. One is picked per run, seeded by the date."""

import random
from dataclasses import dataclass
from datetime import date

from . import config


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    n_contracts: int = config.N_CONTRACTS
    n_usage_seats: int = config.N_USAGE_SEATS
    n_ai_seats: int = config.N_AI_SEATS
    n_inject: int = config.INJECT_PER_RULE
    borderline: bool = False
    messy: bool = False
    conflicts: bool = False


SCENARIOS: dict[str, Scenario] = {
    s.name: s
    for s in (
        Scenario("baseline", "Clean spreadsheets. Injected cases sit well clear of thresholds."),
        Scenario(
            "borderline",
            "Near-miss cases on both sides of every threshold: renewals at 30/31/60/61/90/91 days, "
            "installs at entitlement -1/0/+1, seats idle 89 to 92 days, moderate install growth.",
            borderline=True,
        ),
        Scenario(
            "scale",
            "Eight times the volume with the same noise level.",
            n_contracts=960,
            n_usage_seats=12000,
            n_ai_seats=1600,
            n_inject=12,
        ),
    )
}


def get_scenario(name: str) -> Scenario:
    try:
        return SCENARIOS[name]
    except KeyError:
        raise ValueError(f"unknown scenario {name!r}; choose from {sorted(SCENARIOS)}") from None


def pick_scenario(day: date) -> Scenario:
    """Look random from day to day, but the same date always gives the same scenario."""
    return SCENARIOS[random.Random(day.toordinal()).choice(sorted(SCENARIOS))]
