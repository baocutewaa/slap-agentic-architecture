"""Allocation data structures and candidate evaluation algorithms.

Implements allocation constraints and look-ahead split logic from Sections 2.1, 2.3, and 5.1:
- Single allocation: entire batch into a single location
- Split allocation: dividing batch between two locations when single location has insufficient capacity
- Feasibility constraints: free capacity, MI threshold tau
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from src.model.warehouse_state import WarehouseState, LocationState
from src.model.metrics import calculate_delta_mi


@dataclass
class CandidateAllocation:
    """Represents a potential placement action for an inbound batch."""
    allocations: List[Tuple[str, int]]  # [(location_id, quantity)]
    delta_mi_sum: float
    size_compatible: bool
    is_split: bool = False
    score: float = 0.0
    utility: float = 0.0
    feature_vector: Optional[List[float]] = None


def evaluate_single_allocation(
    location: LocationState,
    sku: str,
    size: float,
    qty: int,
    tau: float = 0.90,
    gamma: float = 0.1
) -> Optional[CandidateAllocation]:
    """Evaluate putting entire quantity into a single location."""
    if location.free_capacity < qty:
        return None

    # Check simulated mixing index threshold
    delta_mi = calculate_delta_mi(location, sku, qty)
    mi_after = location.mixing_index() + delta_mi
    if mi_after > tau:
        return None

    size_compat = location.has_size(size)
    score = -delta_mi + (gamma if size_compat else 0.0)

    return CandidateAllocation(
        allocations=[(location.location_id, qty)],
        delta_mi_sum=delta_mi,
        size_compatible=size_compat,
        is_split=False,
        score=score
    )


def evaluate_split_allocation(
    loc1: LocationState,
    loc2: LocationState,
    sku: str,
    size: float,
    total_qty: int,
    tau: float = 0.90,
    gamma: float = 0.1
) -> Optional[CandidateAllocation]:
    """Evaluate splitting batch into two locations."""
    if loc1.free_capacity <= 0 or loc2.free_capacity <= 0:
        return None
    if loc1.free_capacity + loc2.free_capacity < total_qty:
        return None

    # Greedy split: fill loc1 up to its capacity, remainder into loc2
    qty1 = min(loc1.free_capacity, total_qty - 1)
    qty2 = total_qty - qty1
    if qty2 > loc2.free_capacity or qty1 <= 0 or qty2 <= 0:
        return None

    d_mi1 = calculate_delta_mi(loc1, sku, qty1)
    d_mi2 = calculate_delta_mi(loc2, sku, qty2)

    if (loc1.mixing_index() + d_mi1 > tau) or (loc2.mixing_index() + d_mi2 > tau):
        return None

    size_compat = loc1.has_size(size) or loc2.has_size(size)
    total_delta = d_mi1 + d_mi2
    score = -total_delta + (gamma if size_compat else 0.0)

    return CandidateAllocation(
        allocations=[(loc1.location_id, qty1), (loc2.location_id, qty2)],
        delta_mi_sum=total_delta,
        size_compatible=size_compat,
        is_split=True,
        score=score
    )
