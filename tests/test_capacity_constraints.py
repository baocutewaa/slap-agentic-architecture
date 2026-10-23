"""Unit tests for capacity, inventory constraints, and Phase 2 snapshot state creation.

Reference: Sections 2.1, 4.4, 7 (Phase 2), and 8.2 of the Plan.
Validates:
- Capacity invariant (max 18 slots per location, no overflow)
- No negative inventory constraints
- Normalized long-format interim snapshots integrity
- Exact ~20% capacity release (seed=42)
- State after release: free capacity, occupancy rate, released slot tracking
- MI baseline before vs initial MI after release
- Reproducibility of capacity release
"""

from pathlib import Path
import pandas as pd
import pytest

from src.model.warehouse_state import WarehouseState, LocationState
from src.model.state_manager import build_and_process_scope


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
    released = state.release_random_capacity(release_ratio=0.20, seed=42)
    # Exactly 20% released: 180 * 0.2 = 36
    assert len(released) == 36
    assert state.total_occupied_units() == 144
    assert state.free_capacity() == 36


def test_phase2_interim_long_snapshots():
    """Verify interim normalized long snapshots match data audit dimensions."""
    interim_dir = Path("data/interim")

    # Primary scope z in {3, 4}
    df_z34 = pd.read_csv(interim_dir / "random_storage_long_z34.csv")
    assert len(df_z34) == 10800  # 600 * 18
    assert df_z34["originalLocation"].nunique() == 600
    assert set(df_z34.columns) >= {"originalLocation", "slot_id", "Reference", "size", "x", "y", "z"}
    assert df_z34["Reference"].isna().sum() == 0
    assert df_z34["size"].min() == 4.0
    assert df_z34["size"].max() == 16.0

    # Sensitivity scopes
    df_z3 = pd.read_csv(interim_dir / "random_storage_long_z3.csv")
    assert len(df_z3) == 5418  # 301 * 18
    assert df_z3["originalLocation"].nunique() == 301

    df_z4 = pd.read_csv(interim_dir / "random_storage_long_z4.csv")
    assert len(df_z4) == 5382  # 299 * 18
    assert df_z4["originalLocation"].nunique() == 299

    # All levels
    df_all = pd.read_csv(interim_dir / "random_storage_long_all.csv")
    assert len(df_all) == 41256  # 2292 * 18
    assert df_all["originalLocation"].nunique() == 2292


def test_phase2_processed_state_and_released_slots():
    """Verify processed state files after 20% capacity release."""
    processed_dir = Path("data/processed")

    # 1. Released slots file
    df_rel = pd.read_csv(processed_dir / "released_slots_z34_seed42.csv")
    assert len(df_rel) == 2160  # exactly 20% of 10,800
    assert df_rel["seed"].iloc[0] == 42
    # Ensure all released (location, slot_id) are unique
    assert len(df_rel.drop_duplicates(subset=["originalLocation", "slot_id"])) == 2160

    # 2. State after release file
    df_state_after = pd.read_csv(processed_dir / "initial_state_z34_after_release.csv")
    assert len(df_state_after) == 600
    assert df_state_after["occupied"].sum() == 8640  # 10,800 - 2,160
    assert df_state_after["free_capacity"].sum() == 2160
    assert (df_state_after["occupied"] <= 18).all()
    assert (df_state_after["occupied"] >= 0).all()

    # 3. Warehouse slots detailed file
    df_slots = pd.read_csv(processed_dir / "warehouse_slots_state_z34.csv")
    assert len(df_slots) == 10800
    assert df_slots["is_released"].sum() == 2160
    assert df_slots["is_occupied"].sum() == 8640


def test_phase2_baseline_and_initial_after_release_mixing_index():
    """Verify pre-release paper-like baseline MI and post-release initial simulation MI."""
    summary_df = pd.read_csv("outputs/tables/snapshot_mi_before_after_release.csv")
    z34_row = summary_df[summary_df["scope_name"].str.contains("z in {3, 4}")].iloc[0]

    # Baseline before release: closely matches paper reported 0.918 (within 0.5%)
    assert 0.910 <= z34_row["baseline_mi_before"] <= 0.920
    assert z34_row["critical_locations_before_pct"] > 99.0

    # Initial after release: slightly lower due to free capacity
    assert 0.895 <= z34_row["initial_mi_after_release"] <= 0.910
    assert z34_row["occupied_units_after"] == 8640
    assert z34_row["free_capacity_after"] == 2160
    assert z34_row["occupancy_rate_after_pct"] == 80.0


def test_phase2_capacity_release_reproducibility():
    """Re-running release with the same seed must produce identical released slots and state."""
    df_long = pd.read_csv("data/interim/random_storage_long_z34.csv")

    res1 = build_and_process_scope(df_long, "TestScope", release_ratio=0.20, seed=42)
    res2 = build_and_process_scope(df_long, "TestScope", release_ratio=0.20, seed=42)

    assert res1["metrics"] == res2["metrics"]
    pd.testing.assert_frame_equal(res1["df_released"], res2["df_released"])
    pd.testing.assert_frame_equal(res1["df_locs_after"], res2["df_locs_after"])

