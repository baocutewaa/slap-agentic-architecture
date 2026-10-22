"""Abstract base agent defining the unified Perception-Decision-Action loop.

Reference: Section 5.2 of the plan.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from src.model.warehouse_state import WarehouseState
from src.model.allocation import CandidateAllocation, evaluate_single_allocation, evaluate_split_allocation


@dataclass
class ActionDecision:
    """Detailed record of an agent's decision for an inbound event."""
    event_id: int
    agent_mode: str
    sku: str
    size: float
    quantity: int
    status: str  # 'executed', 'pending_manual', 'no_feasible_location', 'infeasible_event'
    reason: str
    selected_allocation: Optional[CandidateAllocation] = None
    mi_before: float = 0.0
    mi_after: float = 0.0
    delta_mi: float = 0.0
    utility: float = 0.0
    weights_before: Optional[List[float]] = None
    weights_after: Optional[List[float]] = None
    runtime_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract Base Class for SLAP agents."""

    def __init__(self, mode_name: str, tau: float = 0.90, top_k: int = 10):
        self.mode_name = mode_name
        self.tau = tau
        self.top_k = top_k

    def generate_candidates(
        self,
        state: WarehouseState,
        sku: str,
        size: float,
        qty: int,
        gamma: float = 0.1
    ) -> List[CandidateAllocation]:
        """Generate feasible candidate allocations (both single location and split)."""
        candidates: List[CandidateAllocation] = []

        # 1. Single allocations
        candidate_locs = [
            loc for loc in state.locations.values() if loc.free_capacity >= qty
        ]
        for loc in candidate_locs:
            alloc = evaluate_single_allocation(loc, sku, size, qty, tau=self.tau, gamma=gamma)
            if alloc is not None:
                candidates.append(alloc)

        # 2. Split allocations if no single candidate or for lookahead exploration
        if len(candidates) == 0 and qty > 1:
            locs_with_space = sorted(
                [loc for loc in state.locations.values() if loc.free_capacity > 0],
                key=lambda l: l.free_capacity,
                reverse=True
            )[:self.top_k]

            for i in range(len(locs_with_space)):
                for j in range(i + 1, len(locs_with_space)):
                    alloc = evaluate_split_allocation(
                        locs_with_space[i],
                        locs_with_space[j],
                        sku,
                        size,
                        qty,
                        tau=self.tau,
                        gamma=gamma
                    )
                    if alloc is not None:
                        candidates.append(alloc)

        return candidates

    def apply_action(
        self,
        state: WarehouseState,
        allocation: CandidateAllocation,
        sku: str,
        size: float
    ) -> None:
        """Apply an approved allocation directly to warehouse state."""
        for loc_id, alloc_qty in allocation.allocations:
            state.get_location(loc_id).add_items(sku, size, alloc_qty)

    @abstractmethod
    def process_event(
        self,
        event: Dict[str, Any],
        state: WarehouseState
    ) -> ActionDecision:
        """Execute unified perceive -> evaluate -> decide -> supervise -> act -> learn loop."""
        pass
