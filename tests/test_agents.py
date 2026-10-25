"""Unit tests for the three Agent modes: Heuristic, Supervised, and Adaptive.

Reference: Sections 2.3, 2.4, 2.5, 5.2, 7 (Phase 5), and 8.3 of the Plan.
"""

import copy
import numpy as np
import pytest

from src.agents import HeuristicAgent, SupervisedAgent, AdaptiveAgent
from src.model.warehouse_state import WarehouseState, LocationState


def create_sample_state() -> WarehouseState:
    """Helper to build a small controlled warehouse state for testing."""
    ws = WarehouseState(capacity_per_location=18, scope_name="agent_test")
    
    # L1: Homogeneous with SKU_A, free = 8
    loc1 = LocationState("L1", capacity=18)
    loc1.add_items("SKU_A", 9.0, 10)
    
    # L2: Mixed with SKU_B and SKU_C, free = 6
    loc2 = LocationState("L2", capacity=18)
    loc2.add_items("SKU_B", 9.0, 6)
    loc2.add_items("SKU_C", 9.0, 6)
    
    # L3: Almost full, free = 1
    loc3 = LocationState("L3", capacity=18)
    loc3.add_items("SKU_D", 9.0, 17)

    ws.add_location(loc1)
    ws.add_location(loc2)
    ws.add_location(loc3)
    return ws


def test_heuristic_agent_execution():
    """HeuristicAgent selects highest scoring candidate and updates warehouse state."""
    state = create_sample_state()
    initial_occupied = state.total_occupied_units()
    
    agent = HeuristicAgent(gamma=0.1, tau=0.95)
    event = {"event_id": 1, "reference": "SKU_A", "size": 9.0, "quantity": 4}
    
    decision = agent.process_event(event, state)
    assert decision.status == "executed"
    assert decision.selected_allocation is not None
    # SKU_A should be consolidated into L1
    assert decision.selected_allocation.primary_location == "L1"
    assert state.total_occupied_units() == initial_occupied + 4
    assert state.get_location("L1").occupied == 14


def test_heuristic_agent_no_feasible_location():
    """HeuristicAgent reports no_feasible_location if batch cannot fit anywhere."""
    state = create_sample_state()
    initial_occupied = state.total_occupied_units()
    
    agent = HeuristicAgent(gamma=0.1, tau=0.95, allow_split=False)
    # Quantity 10 exceeds max single free capacity (L1 free = 8)
    event = {"event_id": 2, "reference": "SKU_X", "size": 9.0, "quantity": 10}
    
    decision = agent.process_event(event, state)
    assert decision.status == "no_feasible_location"
    assert state.total_occupied_units() == initial_occupied


def test_supervised_agent_auto_approve():
    """SupervisedAgent auto-approves consolidation event when Delta MI <= 0."""
    state = create_sample_state()
    initial_occupied = state.total_occupied_units()
    
    agent = SupervisedAgent(gamma=0.1, tau=0.95, auto_approval_rule="delta_mi_le_zero")
    # Inbound SKU_A to L1 which already has dominant SKU_A -> Delta MI <= 0
    event = {"event_id": 3, "reference": "SKU_A", "size": 9.0, "quantity": 3}
    
    decision = agent.process_event(event, state)
    assert decision.status == "executed"
    assert "Auto-approved" in decision.reason
    assert state.total_occupied_units() == initial_occupied + 3


def test_supervised_agent_pending_manual():
    """SupervisedAgent holds event as pending_manual when Delta MI > 0 without mutating state."""
    state = create_sample_state()
    initial_occupied = state.total_occupied_units()
    
    agent = SupervisedAgent(gamma=0.1, tau=0.95, operator_fallback="pending_manual")
    # Inbound brand new SKU_Z -> will increase mixing index -> Delta MI > 0
    event = {"event_id": 4, "reference": "SKU_Z", "size": 9.0, "quantity": 2}
    
    decision = agent.process_event(event, state)
    assert decision.status == "pending_manual"
    assert "requires supervisor" in decision.reason
    # Warehouse state must remain completely unaltered!
    assert state.total_occupied_units() == initial_occupied


def test_supervised_agent_always_approve_sensitivity():
    """SupervisedAgent executes pending proposal if operator_fallback is always_approve."""
    state = create_sample_state()
    initial_occupied = state.total_occupied_units()
    
    agent = SupervisedAgent(gamma=0.1, tau=0.95, operator_fallback="always_approve")
    event = {"event_id": 5, "reference": "SKU_Z", "size": 9.0, "quantity": 2}
    
    decision = agent.process_event(event, state)
    assert decision.status == "executed"
    assert "Manual approval" in decision.reason
    assert state.total_occupied_units() == initial_occupied + 2


def test_adaptive_agent_utility_and_weights_update():
    """AdaptiveAgent computes multi-criteria utility and updates weights online."""
    state = create_sample_state()
    
    agent = AdaptiveAgent(
        learning_rate_eta=0.05,
        regularization_lambda=0.01,
        epsilon_exploration=0.0,  # Pure exploitation for determinism
        seed=42
    )
    
    w_initial = agent.weights.copy()
    assert len(w_initial) == 6
    assert pytest.approx(np.linalg.norm(w_initial), rel=1e-5) == 1.0
    
    event = {"event_id": 6, "reference": "SKU_A", "size": 9.0, "quantity": 2}
    decision = agent.process_event(event, state)
    
    assert decision.status == "executed"
    assert decision.selected_allocation is not None
    assert decision.weights_before is not None
    assert decision.weights_after is not None
    
    # Weights should be updated after observing reward
    w_updated = agent.weights
    assert not np.allclose(w_initial, w_updated)
    # Weights must remain normalized and free of NaNs
    assert pytest.approx(np.linalg.norm(w_updated), rel=1e-5) == 1.0
    assert not np.isnan(w_updated).any()
    assert not np.isinf(w_updated).any()


def test_adaptive_agent_determinism_when_epsilon_zero():
    """AdaptiveAgent with epsilon=0 is strictly deterministic on identical state."""
    state1 = create_sample_state()
    state2 = create_sample_state()
    
    agent1 = AdaptiveAgent(epsilon_exploration=0.0, seed=42)
    agent2 = AdaptiveAgent(epsilon_exploration=0.0, seed=42)
    
    event = {"event_id": 7, "reference": "SKU_A", "size": 9.0, "quantity": 3}
    dec1 = agent1.process_event(event, state1)
    dec2 = agent2.process_event(event, state2)
    
    assert dec1.selected_allocation.allocations == dec2.selected_allocation.allocations
    assert pytest.approx(dec1.utility, rel=1e-5) == dec2.utility
    assert np.allclose(agent1.weights, agent2.weights)


def test_small_stream_execution_all_agents():
    """Execute a 5-event sequence across all 3 agent modes on identical initial states."""
    events = [
        {"event_id": 1, "reference": "SKU_A", "size": 9.0, "quantity": 2},
        {"event_id": 2, "reference": "SKU_B", "size": 9.0, "quantity": 1},
        {"event_id": 3, "reference": "SKU_C", "size": 9.0, "quantity": 3},
        {"event_id": 4, "reference": "SKU_A", "size": 9.0, "quantity": 2},
        {"event_id": 5, "reference": "SKU_NEW", "size": 9.0, "quantity": 2},
    ]
    
    base_state = create_sample_state()
    
    for AgentClass, kwargs in [
        (HeuristicAgent, {"gamma": 0.1, "tau": 0.95}),
        (SupervisedAgent, {"gamma": 0.1, "tau": 0.95, "operator_fallback": "pending_manual"}),
        (AdaptiveAgent, {"learning_rate_eta": 0.05, "epsilon_exploration": 0.0, "tau": 0.95}),
    ]:
        state = copy.deepcopy(base_state)
        agent = AgentClass(**kwargs)
        
        for ev in events:
            dec = agent.process_event(ev, state)
            assert dec.status in ["executed", "pending_manual", "no_feasible_location"]
            # Enforce capacity constraint invariant
            for loc in state.locations.values():
                assert loc.occupied <= 18
                assert loc.free_capacity >= 0
