"""Mixing Index and warehouse evaluation metrics module.

Implements mathematical formulations from Sections 2.1, 2.2, and 8.1 of the Plan:
- Location Mixing Index (MI): MI_l = 1 - (max_i n_i / sum_i n_i) if occupied > 0 else 0.0
- Delta MI before and after potential allocation: delta_mi = MI_after - MI_before
- Delta MI for split allocations across two locations
- Global average Mixing Index across warehouse: mean(MI_l)
- Critical location rate: percentage of locations with MI_l > threshold (default 0.8)
- SKU dispersion: proportion of locations containing the SKU over total locations
"""

from typing import Dict, List, Any, Tuple, Optional, Union
import numpy as np


def calculate_mixing_index(sku_counts: Dict[str, int]) -> float:
    """Calculate Mixing Index (MI) given a dictionary of SKU counts.
    
    Mathematical definition:
        MI = 1 - (max_i n_i / sum_i n_i) if sum_i n_i > 0 else 0.0
        
    Properties:
        - Empty location: MI = 0.0
        - Single SKU: MI = 0.0
        - 18 different SKUs: MI = 17/18 ~= 0.9444
        - 9 of A and 9 of B: MI = 0.5
        - Bounded strictly in [0.0, 1.0) for finite positive quantities.
    """
    total = sum(sku_counts.values())
    if total <= 0:
        return 0.0
    max_count = max(sku_counts.values())
    return float(1.0 - (max_count / total))


def calculate_delta_mi(
    location: Any,
    incoming_sku: str,
    incoming_qty: int
) -> float:
    """Calculate simulated delta MI if incoming_qty of incoming_sku were added to location.
    
    delta_mi = MI_after - MI_before
    - delta_mi < 0: mixing reduced (homogeneity improved / consolidation)
    - delta_mi = 0: mixing unchanged (e.g. pure consolidation of dominant SKU)
    - delta_mi > 0: mixing increased (heterogeneity increased)
    """
    if incoming_qty <= 0:
        return 0.0

    mi_before = location.mixing_index()
    sku_clean = str(incoming_sku).strip()

    # Simulate inventory counts
    virtual_counts = dict(location.sku_counts)
    virtual_counts[sku_clean] = virtual_counts.get(sku_clean, 0) + incoming_qty
    mi_after = calculate_mixing_index(virtual_counts)

    return float(mi_after - mi_before)


def calculate_delta_mi_split(
    loc1: Any,
    loc2: Any,
    incoming_sku: str,
    qty1: int,
    qty2: int
) -> Tuple[float, float, float]:
    """Calculate delta MI for both locations in a split allocation.
    
    Returns:
        (delta_mi_1, delta_mi_2, total_delta_mi)
    """
    d1 = calculate_delta_mi(loc1, incoming_sku, qty1) if qty1 > 0 else 0.0
    d2 = calculate_delta_mi(loc2, incoming_sku, qty2) if qty2 > 0 else 0.0
    return float(d1), float(d2), float(d1 + d2)


def calculate_warehouse_metrics(state: Any, critical_threshold: float = 0.8) -> Dict[str, float]:
    """Calculate comprehensive warehouse metrics snapshot across all active locations."""
    mi_values = [loc.mixing_index() for loc in state.locations.values()]
    total_locs = len(mi_values)

    if total_locs == 0:
        return {
            "average_mi": 0.0,
            "critical_locations_pct": 0.0,
            "critical_locations_count": 0,
            "total_occupied_units": 0,
            "total_capacity": 0,
            "free_capacity": 0,
            "occupancy_rate_pct": 0.0,
        }

    avg_mi = float(np.mean(mi_values))
    critical_count = sum(1 for mi in mi_values if mi > critical_threshold)
    critical_pct = float(critical_count / total_locs * 100.0)
    total_occ = state.total_occupied_units()
    total_cap = state.total_capacity()
    free_cap = max(0, total_cap - total_occ)
    occupancy_pct = (total_occ / total_cap * 100.0) if total_cap > 0 else 0.0

    return {
        "average_mi": round(avg_mi, 4),
        "critical_locations_pct": round(critical_pct, 2),
        "critical_locations_count": critical_count,
        "total_occupied_units": total_occ,
        "total_capacity": total_cap,
        "free_capacity": free_cap,
        "occupancy_rate_pct": round(occupancy_pct, 2),
    }


def calculate_sku_dispersion(state: Any, sku: str) -> float:
    """Calculate dispersion of an SKU across warehouse locations.
    
    Dispersion(i_t) = (# locations containing i_t) / (total locations)
    """
    total_locs = len(state.locations)
    if total_locs == 0:
        return 0.0
    clean_sku = str(sku).strip()
    containing = sum(1 for loc in state.locations.values() if loc.has_sku(clean_sku))
    return float(containing / total_locs)
