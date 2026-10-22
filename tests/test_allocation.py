"""Unit tests for single and split candidate allocation evaluation.

Reference: Sections 2.1, 2.3, and 8.2 of the Plan.
"""

from src.model.warehouse_state import LocationState
from src.model.allocation import evaluate_single_allocation, evaluate_split_allocation


def test_evaluate_single_allocation_feasible():
    """Feasible single allocation when capacity and MI are satisfied."""
    loc = LocationState("L1", capacity=18)
    loc.add_items("SKU_A", 9.0, 10)  # free = 8

    alloc = evaluate_single_allocation(loc, "SKU_A", 9.0, 5, tau=0.95, gamma=0.1)
    assert alloc is not None
    assert alloc.is_split is False
    assert alloc.allocations == [("L1", 5)]
    assert alloc.delta_mi_sum <= 0  # Consolidation doesn't worsen MI


def test_evaluate_single_allocation_insufficient_capacity():
    """Allocation must be None if quantity exceeds free capacity."""
    loc = LocationState("L1", capacity=18)
    loc.add_items("SKU_A", 9.0, 16)  # free = 2

    alloc = evaluate_single_allocation(loc, "SKU_B", 9.0, 4, tau=0.95)
    assert alloc is None


def test_evaluate_split_allocation_feasible():
    """Feasible split allocation across two locations."""
    loc1 = LocationState("L1", capacity=18)
    loc1.add_items("SKU_A", 9.0, 15)  # free = 3

    loc2 = LocationState("L2", capacity=18)
    loc2.add_items("SKU_B", 9.0, 14)  # free = 4

    alloc = evaluate_split_allocation(loc1, loc2, "SKU_C", 9.0, total_qty=6, tau=0.95)
    assert alloc is not None
    assert alloc.is_split is True
    # loc1 gets 3, loc2 gets 3 (total 6)
    total_alloc_qty = sum(q for _, q in alloc.allocations)
    assert total_alloc_qty == 6
