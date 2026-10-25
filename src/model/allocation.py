"""Allocation data structures and candidate evaluation engine.

Implements allocation feasibility constraints and look-ahead split logic from Sections 2.1, 2.3, 2.5, 5.1, and 8.2:
- CandidateAllocation: data structure for single and split candidate placements
- evaluate_single_allocation: checks capacity, computes delta MI, checks safety threshold tau, computes score
- evaluate_split_allocation: optimal/greedy split partition across two locations with exact quantity conservation
- generate_candidate_allocations: warehouse-wide candidate search engine with top-K candidate ranking
- extract_allocation_features: 6-dimensional multi-criteria feature vector for Adaptive Agent
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any, Union
import numpy as np

from src.model.warehouse_state import WarehouseState, LocationState
from src.model.metrics import calculate_delta_mi, calculate_sku_dispersion


@dataclass
class CandidateAllocation:
    """Represents a potential storage allocation action for an inbound batch.
    
    Attributes:
        allocations: List of (location_id, quantity) pairs.
        delta_mi_sum: Total change in mixing index (sum of delta_mi across allocated locations).
        size_compatible: True if at least one allocated location already contains the item's size.
        is_split: False for single-location placement, True for split placement across 2 locations.
        score: Heuristic evaluation score: Score = -delta_mi_sum + gamma * 1(size_compatible).
        utility: Multi-criteria utility for Adaptive Agent (w^T * x).
        feature_vector: 6-dimensional feature vector for Adaptive Agent.
        mi_before_list: List of MI values before allocation for each allocated location.
        mi_after_list: List of MI values after allocation for each allocated location.
        delta_mi_list: List of delta MI for each allocated location.
        status: Feasibility status ("feasible", "rejected_by_capacity", "rejected_by_tau", "rejected_by_quantity").
        rejection_reason: Human-readable explanation if rejected.
    """
    allocations: List[Tuple[str, int]]
    delta_mi_sum: float
    size_compatible: bool
    is_split: bool = False
    score: float = 0.0
    utility: float = 0.0
    feature_vector: Optional[List[float]] = None
    mi_before_list: Optional[List[float]] = None
    mi_after_list: Optional[List[float]] = None
    delta_mi_list: Optional[List[float]] = None
    status: str = "feasible"
    rejection_reason: Optional[str] = None

    @property
    def total_quantity(self) -> int:
        """Total units allocated across all target locations."""
        return sum(q for _, q in self.allocations)

    @property
    def primary_location(self) -> str:
        """Primary target location identifier."""
        return self.allocations[0][0] if self.allocations else ""

    def is_valid_for_quantity(self, expected_qty: int) -> bool:
        """Verify exact conservation of batch units and positive allocations."""
        if self.total_quantity != expected_qty:
            return False
        return all(q > 0 for _, q in self.allocations)


def evaluate_single_allocation(
    location: LocationState,
    sku: str,
    size: float,
    qty: int,
    tau: float = 0.95,
    gamma: float = 0.1
) -> Optional[CandidateAllocation]:
    """Evaluate placing an entire inbound quantity into a single location.
    
    Checks:
        1. Free capacity bound: qty <= location.free_capacity
        2. Mixing index safety threshold: MI_after <= tau
        
    Computes:
        delta_mi = MI_after - MI_before
        score = -delta_mi + gamma * 1(size_compatible)
        
    Returns:
        CandidateAllocation if feasible, or None if capacity / tau threshold is violated.
    """
    if qty <= 0:
        return None

    if location.free_capacity < qty:
        return None

    mi_before = location.mixing_index()
    delta_mi = calculate_delta_mi(location, sku, qty)
    mi_after = mi_before + delta_mi

    # Enforce safety threshold constraint
    if mi_after > tau:
        return None

    size_compat = location.has_size(size)
    score = -delta_mi + (gamma if size_compat else 0.0)

    return CandidateAllocation(
        allocations=[(location.location_id, qty)],
        delta_mi_sum=round(delta_mi, 6),
        size_compatible=size_compat,
        is_split=False,
        score=round(score, 6),
        mi_before_list=[round(mi_before, 6)],
        mi_after_list=[round(mi_after, 6)],
        delta_mi_list=[round(delta_mi, 6)],
        status="feasible"
    )


def evaluate_split_allocation(
    loc1: LocationState,
    loc2: LocationState,
    sku: str,
    size: float,
    total_qty: int,
    tau: float = 0.95,
    gamma: float = 0.1,
    strategy: str = "optimal"
) -> Optional[CandidateAllocation]:
    """Evaluate dividing an inbound batch across two distinct locations.
    
    Constraints:
        - loc1 != loc2
        - total_qty >= 2
        - qty1 + qty2 == total_qty, with 1 <= qty1 <= loc1.free_capacity and 1 <= qty2 <= loc2.free_capacity
        - loc1.free_capacity + loc2.free_capacity >= total_qty
        - MI_after(loc1) <= tau and MI_after(loc2) <= tau
        
    Strategies:
        - "optimal": tests all feasible integer partition points and selects the one maximizing score.
        - "greedy": fills loc1 up to capacity, puts remainder into loc2.
    """
    if loc1.location_id == loc2.location_id:
        return None
    if total_qty < 2:
        return None
    if loc1.free_capacity <= 0 or loc2.free_capacity <= 0:
        return None
    if loc1.free_capacity + loc2.free_capacity < total_qty:
        return None

    # Feasible partition interval for qty1
    min_qty1 = max(1, total_qty - loc2.free_capacity)
    max_qty1 = min(loc1.free_capacity, total_qty - 1)
    if min_qty1 > max_qty1:
        return None

    if strategy == "greedy":
        candidate_splits = [(max_qty1, total_qty - max_qty1)]
    else:  # optimal
        candidate_splits = [
            (q1, total_qty - q1) for q1 in range(min_qty1, max_qty1 + 1)
        ]

    best_allocation: Optional[CandidateAllocation] = None
    best_score = -float("inf")

    mi_before_1 = loc1.mixing_index()
    mi_before_2 = loc2.mixing_index()

    for q1, q2 in candidate_splits:
        d1 = calculate_delta_mi(loc1, sku, q1)
        d2 = calculate_delta_mi(loc2, sku, q2)

        after_1 = mi_before_1 + d1
        after_2 = mi_before_2 + d2

        # Check safety threshold on both locations
        if after_1 > tau or after_2 > tau:
            continue

        size_compat = loc1.has_size(size) or loc2.has_size(size)
        total_delta = d1 + d2
        score = -total_delta + (gamma if size_compat else 0.0)

        if score > best_score:
            best_score = score
            best_allocation = CandidateAllocation(
                allocations=[(loc1.location_id, q1), (loc2.location_id, q2)],
                delta_mi_sum=round(total_delta, 6),
                size_compatible=size_compat,
                is_split=True,
                score=round(score, 6),
                mi_before_list=[round(mi_before_1, 6), round(mi_before_2, 6)],
                mi_after_list=[round(after_1, 6), round(after_2, 6)],
                delta_mi_list=[round(d1, 6), round(d2, 6)],
                status="feasible"
            )

    return best_allocation


def generate_candidate_allocations(
    state: WarehouseState,
    sku: str,
    size: float,
    quantity: int,
    tau: float = 0.95,
    gamma: float = 0.1,
    allow_split: bool = True,
    top_k_split: int = 30
) -> List[CandidateAllocation]:
    """Generate and rank all feasible candidate allocations for an incoming event.
    
    Workflow:
        1. Evaluates all single-location placements with free_capacity >= quantity.
        2. If allow_split and quantity >= 2:
           Filters top-K promising candidate locations based on consolidation criteria
           and evaluates look-ahead split allocations across pairs.
        3. Sorts all feasible candidates by score in descending order.
    """
    candidates: List[CandidateAllocation] = []

    # 1. Single allocations across all locations
    for loc in state.locations.values():
        if loc.free_capacity >= quantity:
            single_cand = evaluate_single_allocation(
                loc, sku=sku, size=size, qty=quantity, tau=tau, gamma=gamma
            )
            if single_cand is not None:
                candidates.append(single_cand)

    # 2. Look-ahead split allocations across pairs in top-K candidate locations
    if allow_split and quantity >= 2:
        # Prioritize locations with free capacity > 0
        loc_priorities: List[Tuple[float, LocationState]] = []
        for loc in state.locations.values():
            if loc.free_capacity > 0:
                # Priority: existing SKU (+3), matching size (+1), free capacity ratio
                prio = (
                    (3.0 if loc.has_sku(sku) else 0.0)
                    + (1.0 if loc.has_size(size) else 0.0)
                    + (loc.free_capacity / loc.capacity)
                )
                loc_priorities.append((prio, loc))

        loc_priorities.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [loc for _, loc in loc_priorities[:top_k_split]]

        # Evaluate pairs in top-K
        num_top = len(top_candidates)
        for i in range(num_top):
            for j in range(i + 1, num_top):
                l1 = top_candidates[i]
                l2 = top_candidates[j]
                if l1.free_capacity + l2.free_capacity >= quantity:
                    split_cand = evaluate_split_allocation(
                        l1, l2, sku=sku, size=size, total_qty=quantity,
                        tau=tau, gamma=gamma, strategy="optimal"
                    )
                    if split_cand is not None:
                        candidates.append(split_cand)

    # Sort descending by score (or delta_mi ascending)
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def extract_allocation_features(
    state: WarehouseState,
    candidate: CandidateAllocation,
    sku: str,
    size: float
) -> List[float]:
    """Extract 6-dimensional multi-criteria feature vector for Adaptive Agent.
    
    Formula from Section 2.5 of the Plan:
        x_l = [ -delta_mi_l, 1(i_t in l), 1(s_t compatible), a_l/C_l, 1 - MI_l^before, Dispersion(i_t) ]
        
    For split allocation, aggregates features weighted by allocated quantity proportions.
    """
    total_qty = candidate.total_quantity
    dispersion = state.sku_dispersion(sku)

    if not candidate.is_split:
        loc_id, qty = candidate.allocations[0]
        loc = state.get_location(loc_id)
        delta_mi = candidate.delta_mi_sum
        has_sku = 1.0 if loc.has_sku(sku) else 0.0
        has_sz = 1.0 if loc.has_size(size) else 0.0
        free_ratio = float(loc.free_capacity / loc.capacity)
        homogeneity = float(1.0 - loc.mixing_index())

        feature_vector = [
            float(-delta_mi),
            has_sku,
            has_sz,
            free_ratio,
            homogeneity,
            float(dispersion),
        ]
    else:
        # Weighted combination for split allocations
        feat_1 = float(-candidate.delta_mi_sum)
        feat_2 = 0.0
        feat_3 = 0.0
        feat_4 = 0.0
        feat_5 = 0.0

        for loc_id, qty in candidate.allocations:
            weight = qty / total_qty
            loc = state.get_location(loc_id)
            feat_2 += weight * (1.0 if loc.has_sku(sku) else 0.0)
            feat_3 += weight * (1.0 if loc.has_size(size) else 0.0)
            feat_4 += weight * (loc.free_capacity / loc.capacity)
            feat_5 += weight * (1.0 - loc.mixing_index())

        feature_vector = [
            feat_1,
            float(feat_2),
            float(feat_3),
            float(feat_4),
            float(feat_5),
            float(dispersion),
        ]

    candidate.feature_vector = feature_vector
    return feature_vector
