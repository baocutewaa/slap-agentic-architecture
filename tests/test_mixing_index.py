"""Unit tests for Mixing Index calculations and warehouse metrics.

Reference: Sections 2.1, 2.2, and 8.1 of the Plan.
"""

import pytest
from src.model.metrics import (
    calculate_mixing_index,
    calculate_delta_mi,
    calculate_delta_mi_split,
    calculate_warehouse_metrics,
    calculate_sku_dispersion,
)
from src.model.warehouse_state import WarehouseState, LocationState


def test_mixing_index_empty_location():
    """Empty location must have MI = 0."""
    loc = LocationState("L1", capacity=18)
    assert loc.mixing_index() == 0.0
    assert calculate_mixing_index({}) == 0.0


def test_mixing_index_single_sku():
    """18 units of the same SKU must have MI = 0."""
    loc = LocationState("L1", capacity=18)
    loc.add_items("SKU_A", 10.0, 18)
    assert loc.mixing_index() == 0.0


def test_mixing_index_all_different_skus():
    """18 units of 18 distinct SKUs must have MI = 17/18 ~= 0.9444."""
    loc = LocationState("L1", capacity=18)
    for i in range(18):
        loc.add_items(f"SKU_{i}", 10.0, 1)
    expected = 1.0 - (1.0 / 18.0)
    assert pytest.approx(loc.mixing_index(), rel=1e-4) == expected


def test_mixing_index_equal_two_skus():
    """9 units of SKU A and 9 units of SKU B must have MI = 0.5."""
    loc = LocationState("L1", capacity=18)
    loc.add_items("SKU_A", 10.0, 9)
    loc.add_items("SKU_B", 10.0, 9)
    assert pytest.approx(loc.mixing_index(), rel=1e-4) == 0.5


def test_mixing_index_range_invariant():
    """MI must always fall in [0, 1)."""
    loc = LocationState("L1", capacity=18)
    loc.add_items("SKU_A", 10.0, 10)
    loc.add_items("SKU_B", 10.0, 5)
    loc.add_items("SKU_C", 10.0, 3)
    mi = loc.mixing_index()
    assert 0.0 <= mi < 1.0


def test_delta_mi_consolidation():
    """Adding an existing dominant SKU reduces or preserves mixing index (delta_mi <= 0)."""
    loc = LocationState("L1", capacity=18)
    loc.add_items("SKU_A", 10.0, 5)
    loc.add_items("SKU_B", 10.0, 5)  # MI = 0.5
    d_mi = calculate_delta_mi(loc, "SKU_A", 5)  # 10 of A, 5 of B -> MI = 1 - 10/15 = 0.3333
    assert d_mi < 0.0
    assert pytest.approx(d_mi, rel=1e-3) == (1.0 - 10.0 / 15.0) - 0.5


def test_delta_mi_new_sku_increases_mixing():
    """Adding a new SKU to a homogeneous location strictly increases mixing (delta_mi > 0)."""
    loc = LocationState("L1", capacity=18)
    loc.add_items("SKU_A", 10.0, 10)  # MI = 0.0
    d_mi = calculate_delta_mi(loc, "SKU_B", 2)  # 10 of A, 2 of B -> MI = 1 - 10/12 = 0.1667
    assert d_mi > 0.0
    assert pytest.approx(d_mi, rel=1e-3) == (1.0 - 10.0 / 12.0)


def test_delta_mi_split():
    """calculate_delta_mi_split returns correct delta for both locations and their sum."""
    loc1 = LocationState("L1", capacity=18)
    loc1.add_items("SKU_A", 10.0, 6)
    loc1.add_items("SKU_B", 10.0, 6)  # MI = 0.5

    loc2 = LocationState("L2", capacity=18)
    loc2.add_items("SKU_C", 10.0, 10)  # MI = 0.0

    d1, d2, total_d = calculate_delta_mi_split(loc1, loc2, "SKU_A", 3, 2)
    # loc1: 9 of A, 6 of B -> MI = 1 - 9/15 = 0.4 -> d1 = -0.1
    # loc2: 10 of C, 2 of A -> MI = 1 - 10/12 = 0.1667 -> d2 = +0.1667
    assert pytest.approx(d1, rel=1e-3) == -0.1
    assert pytest.approx(d2, rel=1e-3) == (1.0 - 10.0 / 12.0)
    assert pytest.approx(total_d, rel=1e-3) == d1 + d2


def test_warehouse_metrics_calculation():
    """calculate_warehouse_metrics correctly computes mean MI and critical locations."""
    ws = WarehouseState(scope_name="test_scope")
    loc1 = LocationState("L1", capacity=18)
    loc1.add_items("SKU_A", 10.0, 18)  # MI = 0.0

    loc2 = LocationState("L2", capacity=18)
    for i in range(18):
        loc2.add_items(f"SKU_{i}", 10.0, 1)  # MI = 17/18 ~= 0.9444 > 0.8 (critical)

    ws.add_location(loc1)
    ws.add_location(loc2)

    metrics = calculate_warehouse_metrics(ws, critical_threshold=0.8)
    assert pytest.approx(metrics["average_mi"], rel=1e-3) == (0.0 + (17.0 / 18.0)) / 2.0
    assert metrics["critical_locations_count"] == 1
    assert metrics["critical_locations_pct"] == 50.0
    assert metrics["total_occupied_units"] == 36
    assert metrics["total_capacity"] == 36
    assert metrics["free_capacity"] == 0
    assert metrics["occupancy_rate_pct"] == 100.0


def test_sku_dispersion():
    """calculate_sku_dispersion correctly calculates proportion of locations containing the SKU."""
    ws = WarehouseState(scope_name="test_scope")
    loc1 = LocationState("L1", capacity=18)
    loc1.add_items("SKU_A", 10.0, 5)

    loc2 = LocationState("L2", capacity=18)
    loc2.add_items("SKU_B", 10.0, 5)

    loc3 = LocationState("L3", capacity=18)
    loc3.add_items("SKU_A", 10.0, 2)

    ws.add_location(loc1)
    ws.add_location(loc2)
    ws.add_location(loc3)

    # SKU_A is in 2 out of 3 locations -> 2/3 ~= 0.6667
    assert pytest.approx(calculate_sku_dispersion(ws, "SKU_A"), rel=1e-3) == 2.0 / 3.0
    # SKU_B is in 1 out of 3 locations -> 1/3 ~= 0.3333
    assert pytest.approx(calculate_sku_dispersion(ws, "SKU_B"), rel=1e-3) == 1.0 / 3.0
    # SKU_C is in 0 locations -> 0.0
    assert calculate_sku_dispersion(ws, "SKU_C") == 0.0
