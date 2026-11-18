"""Decides which (product, site) combinations get which injected condition."""

from dataclasses import dataclass, field

import numpy as np

from . import config

Combo = tuple[str, str]


@dataclass(frozen=True)
class ComboPlan:
    normal: tuple[Combo, ...]
    contract_only: tuple[Combo, ...]
    inventory_only: tuple[Combo, ...]
    over: frozenset[Combo]
    spike: frozenset[Combo]
    edge_installs: tuple[tuple[Combo, int], ...] = field(default=())
    edge_spike: tuple[tuple[Combo, float], ...] = field(default=())


def plan_combos(
    rng: np.random.Generator,
    product_ids: list[str],
    site_ids: list[str],
    n_contract_only: int,
    n_inventory_only: int,
    n_inject: int,
    edge: bool = False,
) -> ComboPlan:
    combos = [(p, s) for p in product_ids for s in site_ids]
    order = [combos[int(i)] for i in rng.permutation(len(combos))]
    split_a = n_contract_only
    split_b = n_contract_only + n_inventory_only
    normal = tuple(order[split_b:])
    offsets = config.EDGE_INSTALL_OFFSETS * config.N_COMBOS_PER_EDGE
    growths = config.EDGE_SPIKE_GROWTH
    n_edge = len(offsets) + len(growths) if edge else 0
    if len(normal) < 2 * n_inject + n_edge:
        raise ValueError("not enough normal combos for the requested injections")
    start = 2 * n_inject
    spike_start = start + len(offsets)
    edge_installs = edge_spike = ()
    if edge:
        edge_installs = tuple(zip(normal[start:spike_start], offsets, strict=True))
        spike_end = spike_start + len(growths)
        edge_spike = tuple(zip(normal[spike_start:spike_end], growths, strict=True))
    return ComboPlan(
        normal=normal,
        contract_only=tuple(order[:split_a]),
        inventory_only=tuple(order[split_a:split_b]),
        over=frozenset(normal[:n_inject]),
        spike=frozenset(normal[n_inject : 2 * n_inject]),
        edge_installs=edge_installs,
        edge_spike=edge_spike,
    )
