"""Adaptive Agent with multi-criteria utility and online learning.

Reference: Section 2.5 of the plan:
- Linear utility function: U_l = w^T x_l
- Feature vector x_l:
    [-Delta_MI_l, 1(sku in loc), 1(size compatible), free_cap/C_l, 1 - MI_before, Dispersion(sku)]
- Online weight update:
    w <- w - eta * [2 * (U_hat - r_t) * x_bar_t + lambda * w]
- Parameters: eta = 0.05, lambda = 0.01, epsilon = 0.1
"""

import time
from typing import Dict, Any, List, Optional
import numpy as np

from src.agents.base_agent import BaseAgent, ActionDecision
from src.model.warehouse_state import WarehouseState
from src.model.allocation import CandidateAllocation


class AdaptiveAgent(BaseAgent):
    """Adaptive agent optimizing multi-criteria utility through gradient-based online learning."""

    NUM_FEATURES = 6

    def __init__(
        self,
        learning_rate_eta: float = 0.05,
        regularization_lambda: float = 0.01,
        epsilon_exploration: float = 0.1,
        tau: float = 0.90,
        top_k: int = 10,
        reward_mode: str = "global_mi_delta",
        seed: int = 42
    ):
        super().__init__(mode_name="adaptive", tau=tau, top_k=top_k)
        self.eta = learning_rate_eta
        self.reg_lambda = regularization_lambda
        self.epsilon = epsilon_exploration
        self.reward_mode = reward_mode
        self.rng = np.random.default_rng(seed)

        # Initial uniform normalized weights
        w = np.ones(self.NUM_FEATURES, dtype=float)
        self.weights = w / np.linalg.norm(w)

    def extract_features(
        self,
        candidate: CandidateAllocation,
        state: WarehouseState,
        sku: str,
        size: float
    ) -> np.ndarray:
        """Extract normalized feature vector x_l for a candidate allocation."""
        delta_mi = candidate.delta_mi_sum
        
        # Primary location attributes
        loc_id = candidate.allocations[0][0]
        loc = state.get_location(loc_id)
        
        sku_in_loc = 1.0 if loc.has_sku(sku) else 0.0
        size_compat = 1.0 if candidate.size_compatible else 0.0
        free_ratio = loc.free_capacity / loc.capacity
        uniformity = 1.0 - loc.mixing_index()
        dispersion = state.sku_dispersion(sku)

        raw_feat = np.array([
            -delta_mi,
            sku_in_loc,
            size_compat,
            free_ratio,
            uniformity,
            dispersion
        ], dtype=float)

        return raw_feat

    def compute_utility(self, features: np.ndarray) -> float:
        """Compute scalar utility U = w^T x."""
        return float(np.dot(self.weights, features))

    def update_weights(self, features: np.ndarray, predicted_utility: float, reward: float) -> None:
        """Update weights online using paper gradient rule:
        w <- w - eta * [2 * (U_hat - r_t) * x_bar_t + lambda * w]
        """
        norm_feat = features / (np.linalg.norm(features) + 1e-8)
        error = predicted_utility - reward
        gradient = 2.0 * error * norm_feat + self.reg_lambda * self.weights
        self.weights = self.weights - self.eta * gradient

        # Maintain normalized weight vector to prevent scale divergence
        w_norm = np.linalg.norm(self.weights)
        if w_norm > 1e-8:
            self.weights = self.weights / w_norm

    def process_event(self, event: Dict[str, Any], state: WarehouseState) -> ActionDecision:
        t0 = time.perf_counter()
        event_id = event["event_id"]
        sku = event["reference"]
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
                reason="No candidate satisfies capacity and MI threshold.",
                mi_before=mi_before,
                mi_after=mi_before,
                delta_mi=0.0,
                weights_before=self.weights.tolist(),
                weights_after=self.weights.tolist(),
                runtime_ms=runtime
            )

        # Compute utility for all candidate allocations
        for c in candidates:
            feat = self.extract_features(c, state, sku, size)
            c.feature_vector = feat.tolist()
            c.utility = self.compute_utility(feat)

        weights_before = self.weights.copy()

        # Epsilon-greedy selection
        if self.rng.random() < self.epsilon and len(candidates) > 1:
            top_k_candidates = sorted(candidates, key=lambda c: c.utility, reverse=True)[:self.top_k]
            selected = self.rng.choice(top_k_candidates)
        else:
            selected = max(candidates, key=lambda c: c.utility)

        # Execute selected allocation
        self.apply_action(state, selected, sku, size)
        mi_after = state.global_mixing_index()

        # Determine observed reward
        if self.reward_mode == "global_mi_delta":
            reward = mi_before - mi_after  # Positive when global MI decreases
        else:
            reward = -selected.delta_mi_sum

        # Online learning update
        self.update_weights(np.array(selected.feature_vector), selected.utility, reward)
        weights_after = self.weights.copy()

        runtime = (time.perf_counter() - t0) * 1000.0

        return ActionDecision(
            event_id=event_id,
            agent_mode=self.mode_name,
            sku=sku,
            size=size,
            quantity=qty,
            status="executed",
            reason="Adaptive multi-criteria candidate executed.",
            selected_allocation=selected,
            mi_before=mi_before,
            mi_after=mi_after,
            delta_mi=selected.delta_mi_sum,
            utility=selected.utility,
            weights_before=weights_before.tolist(),
            weights_after=weights_after.tolist(),
            runtime_ms=runtime
        )
