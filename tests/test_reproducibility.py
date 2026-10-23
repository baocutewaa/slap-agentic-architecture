"""Unit tests for simulation reproducibility and Phase 3 event generator.

Reference: Sections 4, 7 (Phase 3), and 8.3 of the Plan.
Validates:
- Exact reproducibility of event stream generation with seed=42
- Inbound event stream schema, size range, positive quantities, sequential IDs
- 100% SKU membership in Product catalog
- Determinism of Heuristic decision making
- Multi-seed divergence and sensitivity stream validity
"""

from pathlib import Path
import pandas as pd
import pytest

from src.data.event_generator import generate_inbound_stream, validate_inbound_stream
from src.data.loaders import load_raw_csv
from src.agents.heuristic_agent import HeuristicAgent
from src.model.warehouse_state import WarehouseState


def test_event_stream_reproducibility():
    """Event generator produces identical stream given the same random seed."""
    storage_mock = pd.DataFrame([
        {"originalLocation": "L1", "Reference": "REF_1", "size": 9.0},
        {"originalLocation": "L1", "Reference": "REF_2", "size": 10.0},
    ])
    order_mock = pd.DataFrame({"quantity (units)": [1, 2, 3, 5]})

    stream_1 = generate_inbound_stream(storage_mock, order_mock, num_events=50, seed=42)
    stream_2 = generate_inbound_stream(storage_mock, order_mock, num_events=50, seed=42)

    pd.testing.assert_frame_equal(stream_1, stream_2)


def test_heuristic_determinism():
    """Heuristic agent produces identical decision given identical warehouse state and event."""
    event = {"event_id": 1, "reference": "REF_1", "size": 9.0, "quantity": 2}

    def build_test_state():
        state = WarehouseState(capacity_per_location=18)
        l1 = state.add_location("L1")
        l1.add_items("REF_1", 9.0, 10)  # free 8
        l2 = state.add_location("L2")
        l2.add_items("REF_2", 9.0, 10)  # free 8
        return state

    agent1 = HeuristicAgent(gamma=0.1, tau=0.95)
    agent2 = HeuristicAgent(gamma=0.1, tau=0.95)

    s1 = build_test_state()
    s2 = build_test_state()

    dec1 = agent1.process_event(event, s1)
    dec2 = agent2.process_event(event, s2)

    assert dec1.status == dec2.status
    assert dec1.selected_allocation.allocations == dec2.selected_allocation.allocations
    assert dec1.delta_mi == dec2.delta_mi


def test_phase3_primary_event_stream_integrity():
    """Verify generated 10,000-event primary stream satisfies all warehouse invariants."""
    stream_path = Path("data/processed/inbound_events.csv")
    assert stream_path.exists(), "data/processed/inbound_events.csv does not exist"

    df_events = pd.read_csv(stream_path)
    assert len(df_events) == 10000
    assert list(df_events.columns) == ["event_id", "reference", "size", "quantity", "seed"]

    # Sequential event_id from 1 to 10,000
    assert list(df_events["event_id"]) == list(range(1, 10001))
    assert df_events["event_id"].nunique() == 10000

    # 100% SKU in Product catalog
    df_prod = load_raw_csv("Product.csv")
    valid_refs = set(df_prod["Reference"].astype(str).str.strip())
    stream_refs = set(df_events["reference"].astype(str).str.strip())
    assert stream_refs.issubset(valid_refs)
    assert len(stream_refs) == 208

    # Size range strictly between 4.0 and 16.0
    assert float(df_events["size"].min()) == 4.0
    assert float(df_events["size"].max()) == 16.0

    # Positive integer quantities
    assert (df_events["quantity"] >= 1).all()
    assert (df_events["quantity"] % 1 == 0).all()
    assert 1.7 <= df_events["quantity"].mean() <= 2.0
    assert df_events["quantity"].median() == 1.0


def test_phase3_full_scale_reproducibility():
    """Re-generating 1,000 events with seed=42 produces bit-for-bit identical results."""
    df_long_z34 = pd.read_csv("data/interim/random_storage_long_z34.csv")
    df_order = load_raw_csv("Customer_Order.csv")

    stream_a = generate_inbound_stream(df_long_z34, df_order, num_events=1000, seed=42)
    stream_b = generate_inbound_stream(df_long_z34, df_order, num_events=1000, seed=42)

    pd.testing.assert_frame_equal(stream_a, stream_b)

    # Different seed must produce different stream
    stream_c = generate_inbound_stream(df_long_z34, df_order, num_events=1000, seed=99)
    assert not stream_a["reference"].equals(stream_c["reference"])


def test_phase3_demand_proxy_stream():
    """Verify Sensitivity S2 demand-proxy event stream."""
    stream_path = Path("data/processed/inbound_events_demand_proxy_seed42.csv")
    assert stream_path.exists()

    df_events = pd.read_csv(stream_path)
    assert len(df_events) == 10000
    assert float(df_events["size"].min()) >= 4.0
    assert float(df_events["size"].max()) <= 16.0
    assert (df_events["quantity"] >= 1).all()
