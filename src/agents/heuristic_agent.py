"""Heuristic Agent for SLAP.

Reference: Section 2.3 of the plan:
- Evaluates feasible allocations by minimizing Delta MI while adding a size compatibility bonus:
  Score_l = -Delta_MI_l + gamma * 1(size compatible)
- Executes best allocation directly.
"""

import time
from typing import Dict, Any, Optional
from src.agents.base_agent import BaseAgent, ActionDecision
from src.model.warehouse_state import WarehouseState


class HeuristicAgent(BaseAgent):
    """Greedy heuristic minimizing mixing index deterioration with size affinity."""

    def __init__(self, gamma: float = 0.1, tau: float = 0.90, top_k: int = 10):
        super().__init__(mode_name="heuristic", tau=tau, top_k=top_k)
        self.gamma = gamma

    def process_event(self, event: Dict[str, Any], state: WarehouseState) -> ActionDecision:
        t0 = time.perf_counter()
        event_id = event["event_id"]
        sku = event["reference"]
        size = float(event["size"])
        qty = int(event["quantity"])

        mi_before = state.global_mixing_index()

        candidates = self.generate_candidates(state, sku, size, qty, gamma=self.gamma)

        if not candidates:
            runtime = (time.perf_counter() - t0) * 1000.0
            return ActionDecision(
                event_id=event_id,
                agent_mode=self.mode_name,
                sku=sku,
                size=size,
                quantity=qty,
                status="no_feasible_location",
                reason="No candidate location satisfies capacity and MI threshold.",
                mi_before=mi_before,
                mi_after=mi_before,
                delta_mi=0.0,
                runtime_ms=runtime
            )

        # Select candidate with highest score (which minimizes Delta MI)
        best_candidate = max(candidates, key=lambda c: c.score)

        # Execute action
        self.apply_action(state, best_candidate, sku, size)
        mi_after = state.global_mixing_index()
        runtime = (time.perf_counter() - t0) * 1000.0

        return ActionDecision(
            event_id=event_id,
            agent_mode=self.mode_name,
            sku=sku,
            size=size,
            quantity=qty,
            status="executed",
            reason="Heuristic highest score candidate executed.",
            selected_allocation=best_candidate,
            mi_before=mi_before,
            mi_after=mi_after,
            delta_mi=best_candidate.delta_mi_sum,
            runtime_ms=runtime
        )
