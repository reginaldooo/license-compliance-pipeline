"""Decides which (product, site) combinations get which injected condition."""

from dataclasses import dataclass

import numpy as np

Combo = tuple[str, str]


@dataclass(frozen=True)
class ComboPlan:
    normal: tuple[Combo, ...]
    contract_only: tuple[Combo, ...]
    inventory_only: tuple[Combo, ...]
    over: frozenset[Combo]
    spike: frozenset[Combo]


def plan_combos(
    rng: np.random.Generator,
    product_ids: list[str],
    site_ids: list[str],
    n_contract_only: int,
    n_inventory_only: int,
    n_inject: int,
) -> ComboPlan:
    combos = [(p, s) for p in product_ids for s in site_ids]
    order = [combos[int(i)] for i in rng.permutation(len(combos))]
    split_a = n_contract_only
    split_b = n_contract_only + n_inventory_only
    normal = tuple(order[split_b:])
    if len(normal) < 2 * n_inject:
        raise ValueError("not enough normal combos for the requested injections")
    return ComboPlan(
        normal=normal,
        contract_only=tuple(order[:split_a]),
        inventory_only=tuple(order[split_a:split_b]),
        over=frozenset(normal[:n_inject]),
        spike=frozenset(normal[n_inject : 2 * n_inject]),
    )
