"""Unit tests for single and split candidate allocation evaluation, features, and atomic execution.

Reference: Sections 2.1, 2.3, 2.5, 5.1, and 8.2 of the Plan.
"""

import pytest
from src.model.warehouse_state import WarehouseState, LocationState
from src.model.allocation import (
    CandidateAllocation,
    evaluate_single_allocation,
    evaluate_split_allocation,
    generate_candidate_allocations,
    extract_allocation_features,
)


def test_evaluate_single_allocation_feasible():
    """Feasible single allocation when capacity and MI safety threshold are satisfied."""
    loc = LocationState("L1", capacity=18)
    loc.add_items("SKU_A", 9.0, 10)  # free = 8, has size 9.0

    alloc = evaluate_single_allocation(loc, "SKU_A", 9.0, 5, tau=0.95, gamma=0.1)
    assert alloc is not None
    assert alloc.is_split is False
    assert alloc.allocations == [("L1", 5)]
    assert alloc.delta_mi_sum <= 0  # Consolidation of dominant SKU improves/maintains MI
    assert alloc.size_compatible is True
    assert alloc.score >= -alloc.delta_mi_sum


def test_evaluate_single_allocation_insufficient_capacity():
    """Allocation must be None if quantity exceeds free capacity."""
    loc = LocationState("L1", capacity=18)
    loc.add_items("SKU_A", 9.0, 16)  # free = 2

    alloc = evaluate_single_allocation(loc, "SKU_B", 9.0, 4, tau=0.95)
    assert alloc is None


def test_evaluate_single_allocation_rejected_by_tau():
    """Allocation must be None if resulting MI exceeds safety threshold tau."""
    loc = LocationState("L1", capacity=18)
    # Add 1 item each of 8 SKUs (MI = 1 - 1/8 = 0.875)
    for i in range(8):
        loc.add_items(f"SKU_{i}", 9.0, 1)

    # Adding 1 item of SKU_9 makes 9 distinct SKUs: MI_after = 1 - 1/9 = 0.8889
    # If tau = 0.85, this must be rejected!
    alloc = evaluate_single_allocation(loc, "SKU_9", 9.0, 1, tau=0.85)
    assert alloc is None

    # If tau = 0.90, this must be accepted!
    alloc_allowed = evaluate_single_allocation(loc, "SKU_9", 9.0, 1, tau=0.90)
    assert alloc_allowed is not None


def test_evaluate_single_allocation_invalid_quantity():
    """Quantity <= 0 must return None."""
    loc = LocationState("L1", capacity=18)
    assert evaluate_single_allocation(loc, "SKU_A", 9.0, 0) is None
    assert evaluate_single_allocation(loc, "SKU_A", 9.0, -5) is None


def test_evaluate_split_allocation_feasible():
    """Feasible split allocation across two locations with quantity conservation."""
    loc1 = LocationState("L1", capacity=18)
    loc1.add_items("SKU_A", 9.0, 15)  # free = 3

    loc2 = LocationState("L2", capacity=18)
    loc2.add_items("SKU_B", 9.0, 14)  # free = 4

    alloc = evaluate_split_allocation(loc1, loc2, "SKU_C", 9.0, total_qty=6, tau=0.95)
    assert alloc is not None
    assert alloc.is_split is True
    # loc1 gets at most 3, loc2 gets remaining
    total_alloc_qty = sum(q for _, q in alloc.allocations)
    assert total_alloc_qty == 6
    assert alloc.is_valid_for_quantity(6)


def test_evaluate_split_allocation_strategies():
    """Compare optimal and greedy partition strategies in split allocation."""
    loc1 = LocationState("L1", capacity=18)
    loc1.add_items("SKU_A", 9.0, 10)  # free = 8, dominant SKU_A

    loc2 = LocationState("L2", capacity=18)
    loc2.add_items("SKU_B", 9.0, 10)  # free = 8, dominant SKU_B

    # Inbound batch of SKU_A with qty 8
    # Greedy fills loc1 up to max allowed (min(8, 7) = 7) and loc2 with 1
    alloc_greedy = evaluate_split_allocation(loc1, loc2, "SKU_A", 9.0, 8, tau=0.95, strategy="greedy")
    # Optimal tests all partitions (q1 in 1..7) to maximize score
    alloc_optimal = evaluate_split_allocation(loc1, loc2, "SKU_A", 9.0, 8, tau=0.95, strategy="optimal")

    assert alloc_greedy is not None
    assert alloc_optimal is not None
    assert alloc_optimal.score >= alloc_greedy.score


def test_evaluate_split_allocation_rejections():
    """Split allocation must reject same location, quantity < 2, or insufficient combined capacity."""
    loc1 = LocationState("L1", capacity=18)
    loc1.add_items("SKU_A", 9.0, 10)
    loc2 = LocationState("L2", capacity=18)
    loc2.add_items("SKU_B", 9.0, 10)

    # Same location
    assert evaluate_split_allocation(loc1, loc1, "SKU_C", 9.0, 4) is None
    # Quantity < 2
    assert evaluate_split_allocation(loc1, loc2, "SKU_C", 9.0, 1) is None
    # Combined capacity exceeded (free = 8 + 8 = 16, request 17)
    assert evaluate_split_allocation(loc1, loc2, "SKU_C", 9.0, 17) is None


def test_generate_candidate_allocations():
    """Candidate generation evaluates both single and look-ahead split allocations."""
    ws = WarehouseState(scope_name="test_scope")
    # loc1 has free = 3, existing SKU_A
    loc1 = LocationState("L1", capacity=18)
    loc1.add_items("SKU_A", 9.0, 15)

    # loc2 has free = 3, existing SKU_B
    loc2 = LocationState("L2", capacity=18)
    loc2.add_items("SKU_B", 9.0, 15)

    # loc3 has free = 10, existing SKU_C
    loc3 = LocationState("L3", capacity=18)
    loc3.add_items("SKU_C", 9.0, 8)

    ws.add_location(loc1)
    ws.add_location(loc2)
    ws.add_location(loc3)

    # Inbound: SKU_A, size 9.0, qty 5
    # loc1 has 3 free (cannot take all 5)
    # loc2 has 3 free (cannot take all 5)
    # loc3 has 10 free (can take all 5)
    # Split across (loc1, loc2) or (loc1, loc3) can also take 5
    cands = generate_candidate_allocations(ws, "SKU_A", 9.0, 5, tau=0.95, allow_split=True)
    assert len(cands) > 0

    # Ensure candidates are sorted by score descending
    scores = [c.score for c in cands]
    assert scores == sorted(scores, reverse=True)

    # Check that at least one single and one split candidate exist
    has_single = any(not c.is_split for c in cands)
    has_split = any(c.is_split for c in cands)
    assert has_single is True
    assert has_split is True


def test_extract_allocation_features():
    """extract_allocation_features generates a 6D vector within expected bounds."""
    ws = WarehouseState(scope_name="test_scope")
    loc1 = LocationState("L1", capacity=18)
    loc1.add_items("SKU_A", 9.0, 10)  # free = 8
    ws.add_location(loc1)

    alloc_single = evaluate_single_allocation(loc1, "SKU_A", 9.0, 4)
    feat_single = extract_allocation_features(ws, alloc_single, "SKU_A", 9.0)

    assert len(feat_single) == 6
    assert isinstance(feat_single, list)
    # Features: [-delta_mi, has_sku, has_size, free_ratio, homogeneity, dispersion]
    assert feat_single[1] == 1.0  # loc1 has SKU_A
    assert feat_single[2] == 1.0  # loc1 has size 9.0
    assert pytest.approx(feat_single[3], rel=1e-3) == 8.0 / 18.0
    assert pytest.approx(feat_single[4], rel=1e-3) == 1.0  # Homogeneous before (MI=0)
    assert pytest.approx(feat_single[5], rel=1e-3) == 1.0  # In 1/1 locations


def test_apply_allocation_atomic_success_and_quantity_conservation():
    """apply_allocation applies units correctly across locations and updates occupancy."""
    ws = WarehouseState(scope_name="test_scope")
    loc1 = LocationState("L1", capacity=18)
    loc1.add_items("SKU_A", 9.0, 10)
    loc2 = LocationState("L2", capacity=18)
    loc2.add_items("SKU_B", 9.0, 12)
    ws.add_location(loc1)
    ws.add_location(loc2)

    occ_before = ws.total_occupied_units()

    # Split allocation: 4 to L1, 2 to L2 (total 6)
    alloc = CandidateAllocation(
        allocations=[("L1", 4), ("L2", 2)],
        delta_mi_sum=-0.1,
        size_compatible=True,
        is_split=True
    )

    success = ws.apply_allocation("SKU_A", 9.0, alloc, expected_total_qty=6)
    assert success is True
    assert ws.total_occupied_units() == occ_before + 6
    assert loc1.free_capacity == 4  # was 8, added 4
    assert loc2.free_capacity == 4  # was 6, added 2
    assert loc1.sku_counts["SKU_A"] == 14
    assert loc2.sku_counts["SKU_A"] == 2


def test_apply_allocation_quantity_mismatch_raises_error():
    """apply_allocation raises ValueError if sum(allocations) != expected_total_qty."""
    ws = WarehouseState(scope_name="test_scope")
    loc1 = LocationState("L1", capacity=18)
    ws.add_location(loc1)

    alloc = CandidateAllocation(
        allocations=[("L1", 3)],
        delta_mi_sum=0.0,
        size_compatible=False,
    )

    with pytest.raises(ValueError, match="does not match expected"):
        ws.apply_allocation("SKU_A", 9.0, alloc, expected_total_qty=5)


def test_apply_allocation_atomic_rollback_on_failure():
    """apply_allocation leaves state completely untouched if an error occurs midway."""
    ws = WarehouseState(scope_name="test_scope")
    loc1 = LocationState("L1", capacity=18)
    loc1.add_items("SKU_A", 9.0, 15)  # free = 3

    loc2 = LocationState("L2", capacity=18)
    loc2.add_items("SKU_B", 9.0, 17)  # free = 1

    ws.add_location(loc1)
    ws.add_location(loc2)

    occ_before = ws.total_occupied_units()
    l1_counts_before = dict(loc1.sku_counts)
    l2_counts_before = dict(loc2.sku_counts)

    # Attempt allocation: 2 to L1 (fits), 3 to L2 (exceeds L2 free capacity!)
    alloc = CandidateAllocation(
        allocations=[("L1", 2), ("L2", 3)],
        delta_mi_sum=0.0,
        size_compatible=False,
        is_split=True
    )

    with pytest.raises(ValueError, match="Insufficient capacity"):
        ws.apply_allocation("SKU_C", 9.0, alloc)

    # State must be completely unmodified!
    assert ws.total_occupied_units() == occ_before
    assert loc1.sku_counts == l1_counts_before
    assert loc2.sku_counts == l2_counts_before
    assert loc1.free_capacity == 3
    assert loc2.free_capacity == 1


def test_rollback_allocation_explicit():
    """rollback_allocation successfully undoes a previously applied allocation."""
    ws = WarehouseState(scope_name="test_scope")
    loc1 = LocationState("L1", capacity=18)
    loc1.add_items("SKU_A", 9.0, 10)
    loc2 = LocationState("L2", capacity=18)
    loc2.add_items("SKU_B", 9.0, 10)
    ws.add_location(loc1)
    ws.add_location(loc2)

    occ_before = ws.total_occupied_units()

    alloc = CandidateAllocation(
        allocations=[("L1", 4), ("L2", 3)],
        delta_mi_sum=-0.05,
        size_compatible=True,
        is_split=True
    )

    ws.apply_allocation("SKU_C", 9.0, alloc, expected_total_qty=7)
    assert ws.total_occupied_units() == occ_before + 7

    # Now roll it back
    rolled_back = ws.rollback_allocation("SKU_C", 9.0, alloc)
    assert rolled_back is True
    assert ws.total_occupied_units() == occ_before
    assert loc1.sku_counts.get("SKU_C", 0) == 0
    assert loc2.sku_counts.get("SKU_C", 0) == 0
