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

    def __init__(
        self,
        gamma: float = 0.1,
        tau: float = 0.95,
        top_k: int = 30,
        allow_split: bool = True
    ):
        super().__init__(
            mode_name="heuristic",
            tau=tau,
            gamma=gamma,
            top_k=top_k,
            allow_split=allow_split
        )

    def process_event(self, event: Dict[str, Any], state: WarehouseState) -> ActionDecision:
        t0 = time.perf_counter()
        event_id = int(event["event_id"])
        sku = str(event["reference"]).strip()
        size = float(event["size"])
        qty = int(event["quantity"])

        mi_before = state.global_mixing_index()

        candidates = self.generate_candidates(state, sku, size, qty)

        if not candidates:
            runtime = (time.perf_counter() - t0) * 1000.0
            return ActionDecision(
                event_id=event_id,
                agent_mode=self.mode_name,
                sku=sku,
                size=size,
                quantity=qty,
                status="no_feasible_location",
                reason="No candidate location satisfies capacity and MI safety threshold tau.",
                mi_before=mi_before,
                mi_after=mi_before,
                delta_mi=0.0,
                runtime_ms=runtime
            )

        # Candidates are already sorted descending by heuristic score
        best_candidate = candidates[0]

        # Execute action atomically
        self.apply_action(state, best_candidate, sku, size, expected_qty=qty)
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
