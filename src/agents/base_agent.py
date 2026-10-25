"""Abstract base agent defining the unified Perception-Decision-Action loop.

Reference: Sections 2.3, 2.4, 2.5, 5.2, and 7 (Phase 5) of the Plan.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np

from src.model.warehouse_state import WarehouseState
from src.model.allocation import (
    CandidateAllocation,
    generate_candidate_allocations,
)


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
    """Abstract Base Class for SLAP agents defining the unified Perception-Decision-Action loop."""

    def __init__(
        self,
        mode_name: str,
        tau: float = 0.95,
        gamma: float = 0.1,
        top_k: int = 30,
        allow_split: bool = True
    ):
        self.mode_name = mode_name
        self.tau = tau
        self.gamma = gamma
        self.top_k = top_k
        self.allow_split = allow_split

    def generate_candidates(
        self,
        state: WarehouseState,
        sku: str,
        size: float,
        qty: int,
        gamma: Optional[float] = None
    ) -> List[CandidateAllocation]:
        """Generate and rank all feasible candidate allocations (single & look-ahead split)."""
        effective_gamma = gamma if gamma is not None else self.gamma
        return generate_candidate_allocations(
            state=state,
            sku=sku,
            size=size,
            quantity=qty,
            tau=self.tau,
            gamma=effective_gamma,
            allow_split=self.allow_split,
            top_k_split=self.top_k
        )

    def apply_action(
        self,
        state: WarehouseState,
        allocation: CandidateAllocation,
        sku: str,
        size: float,
        expected_qty: Optional[int] = None
    ) -> bool:
        """Apply an approved allocation atomically to the warehouse state."""
        return state.apply_allocation(
            sku=sku,
            size=size,
            allocations=allocation,
            expected_total_qty=expected_qty
        )

    @abstractmethod
    def process_event(
        self,
        event: Dict[str, Any],
        state: WarehouseState
    ) -> ActionDecision:
        """Execute unified perceive -> evaluate -> decide -> supervise -> act -> learn loop."""
        pass
