"""Unit tests for simulation reproducibility.

Reference: Section 8.3 of the Plan.
"""

import pandas as pd
from src.data.event_generator import generate_inbound_stream
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
