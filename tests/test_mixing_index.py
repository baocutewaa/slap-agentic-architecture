"""Unit tests for Mixing Index calculations.

Reference: Section 8.1 of the Plan.
"""

import pytest
from src.model.metrics import calculate_mixing_index
from src.model.warehouse_state import LocationState


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
