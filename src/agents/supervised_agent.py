"""Supervised Agent for progressive autonomy.

Reference: Section 2.4 of the plan:
- Uses the same heuristic evaluation logic as HeuristicAgent.
- Enforces an automated safety gate: auto-approves and executes only if Delta MI <= 0.
- Otherwise, proposals transition to 'pending_manual' without updating warehouse state
  (or executed if operator_fallback == 'always_approve' for sensitivity).
"""

import time
from typing import Dict, Any
from src.agents.base_agent import BaseAgent, ActionDecision
from src.model.warehouse_state import WarehouseState


class SupervisedAgent(BaseAgent):
    """Supervised autonomous agent with approval supervision."""

    def __init__(
        self,
        gamma: float = 0.1,
        tau: float = 0.90,
        top_k: int = 10,
        auto_approval_rule: str = "delta_mi_le_zero",
        operator_fallback: str = "pending_manual"
    ):
        super().__init__(mode_name="supervised", tau=tau, top_k=top_k)
        self.gamma = gamma
        self.auto_approval_rule = auto_approval_rule
        self.operator_fallback = operator_fallback

    def is_auto_approved(self, delta_mi: float) -> bool:
        """Evaluate auto-approval rule."""
        if self.auto_approval_rule == "delta_mi_le_zero":
            return delta_mi <= 1e-9
        elif self.auto_approval_rule == "delta_mi_eq_zero":
            return abs(delta_mi) <= 1e-9
        return False

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
                reason="No candidate satisfies capacity and MI threshold.",
                mi_before=mi_before,
                mi_after=mi_before,
                delta_mi=0.0,
                runtime_ms=runtime
            )

        best_candidate = max(candidates, key=lambda c: c.score)
        approved = self.is_auto_approved(best_candidate.delta_mi_sum)

        if approved:
            # Auto-approved and executed
            self.apply_action(state, best_candidate, sku, size)
            mi_after = state.global_mixing_index()
            status = "executed"
            reason = "Auto-approved: satisfies non-worsening MI condition."
        elif self.operator_fallback == "always_approve":
            # Sensitivity mode: simulated human confirms all feasible proposals
            self.apply_action(state, best_candidate, sku, size)
            mi_after = state.global_mixing_index()
            status = "executed"
            reason = "Manual approval simulated by operator."
        else:
            # Main replication run: conservative pending status, state unchanged
            mi_after = mi_before
            status = "pending_manual"
            reason = f"Delta MI ({best_candidate.delta_mi_sum:.4f}) > 0 requires manual supervisor confirmation."

        runtime = (time.perf_counter() - t0) * 1000.0
        return ActionDecision(
            event_id=event_id,
            agent_mode=self.mode_name,
            sku=sku,
            size=size,
            quantity=qty,
            status=status,
            reason=reason,
            selected_allocation=best_candidate,
            mi_before=mi_before,
            mi_after=mi_after,
            delta_mi=best_candidate.delta_mi_sum if status == "executed" else 0.0,
            runtime_ms=runtime
        )
