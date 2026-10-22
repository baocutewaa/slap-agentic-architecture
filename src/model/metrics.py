"""Mixing Index and evaluation metrics module.

Implements mathematical formulations from Section 2.2:
- Location Mixing Index (MI)
- Delta MI before and after potential allocation
- Global average Mixing Index
- Critical location rate (MI > 0.8)
- SKU dispersion
"""

from typing import Dict, List, Any
import numpy as np
from src.model.warehouse_state import WarehouseState, LocationState


def calculate_mixing_index(sku_counts: Dict[str, int]) -> float:
    """Calculate mixing index given a dictionary of SKU counts.
    
    MI = 1 - (max_i n_i / sum_i n_i) if sum_i n_i > 0 else 0.0
    """
    total = sum(sku_counts.values())
    if total == 0:
        return 0.0
    max_count = max(sku_counts.values())
    return 1.0 - (max_count / total)


def calculate_delta_mi(
    location: LocationState,
    incoming_sku: str,
    incoming_qty: int
) -> float:
    """Simulate delta MI if incoming_qty of incoming_sku were added to location.
    
    delta_mi = MI_after - MI_before
    """
    mi_before = location.mixing_index()
    
    # Virtual count
    virtual_counts = dict(location.sku_counts)
    virtual_counts[incoming_sku] = virtual_counts.get(incoming_sku, 0) + incoming_qty
    mi_after = calculate_mixing_index(virtual_counts)
    
    return mi_after - mi_before


def calculate_warehouse_metrics(state: WarehouseState) -> Dict[str, float]:
    """Calculate comprehensive warehouse metrics snapshot."""
    mi_values = [loc.mixing_index() for loc in state.locations.values()]
    avg_mi = float(np.mean(mi_values)) if mi_values else 0.0
    critical_pct = float(np.mean([1.0 if mi > 0.8 else 0.0 for mi in mi_values]) * 100.0) if mi_values else 0.0
    total_occ = state.total_occupied_units()
    total_cap = state.total_capacity()
    occupancy_pct = (total_occ / total_cap * 100.0) if total_cap > 0 else 0.0

    return {
        "average_mi": avg_mi,
        "critical_locations_pct": critical_pct,
        "total_occupied_units": total_occ,
        "total_capacity": total_cap,
        "occupancy_rate_pct": occupancy_pct,
    }
