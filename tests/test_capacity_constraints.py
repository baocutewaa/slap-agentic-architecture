"""Unit tests for capacity and inventory constraints.

Reference: Section 8.2 of the Plan.
"""

import pytest
from src.model.warehouse_state import WarehouseState, LocationState


def test_capacity_bound():
    """Occupied capacity must not exceed 18."""
    loc = LocationState("L1", capacity=18)
    loc.add_items("SKU_1", 8.0, 15)
    assert loc.free_capacity == 3

    with pytest.raises(ValueError):
        loc.add_items("SKU_2", 8.0, 4)  # 15 + 4 > 18


def test_no_negative_inventory():
    """Cannot remove more items than present."""
    loc = LocationState("L1", capacity=18)
    loc.add_items("SKU_1", 8.0, 5)

    with pytest.raises(ValueError):
        loc.remove_items("SKU_1", 8.0, 6)


def test_capacity_release():
    """Initial capacity release reduces occupancy and creates free slots."""
    state = WarehouseState(capacity_per_location=18)
    for i in range(10):
        loc = state.add_location(f"LOC_{i}")
        loc.add_items("SKU_A", 10.0, 18)

    assert state.total_occupied_units() == 180
    state.release_random_capacity(release_ratio=0.20, seed=42)
    # Approx 20% released
    assert state.total_occupied_units() == 144
