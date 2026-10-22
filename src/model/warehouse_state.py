"""Warehouse state representation and state management.

Tracks location inventories, free capacity, sizes, and coordinates.
Supports releasing ~20% initial capacity and atomic allocation updates.
"""

from typing import Dict, List, Optional, Tuple, Set
import numpy as np
import pandas as pd


class LocationState:
    """State of an individual storage location."""

    def __init__(self, location_id: str, capacity: int = 18, coordinates: Optional[Tuple[float, float, float]] = None):
        self.location_id = location_id
        self.capacity = capacity
        self.coordinates = coordinates or (0.0, 0.0, 0.0)
        self.sku_counts: Dict[str, int] = {}
        self.size_counts: Dict[float, int] = {}

    @property
    def occupied(self) -> int:
        return sum(self.sku_counts.values())

    @property
    def free_capacity(self) -> int:
        return max(0, self.capacity - self.occupied)

    def mixing_index(self) -> float:
        """Calculate Mixing Index (MI) for this location.
        
        MI = 1 - (max_i n_i / sum_i n_i) if occupied > 0 else 0.0
        """
        total = self.occupied
        if total == 0:
            return 0.0
        max_sku_qty = max(self.sku_counts.values())
        return 1.0 - (max_sku_qty / total)

    def has_size(self, size: float) -> bool:
        """Check if location contains items with the specified size."""
        return self.size_counts.get(size, 0) > 0

    def has_sku(self, sku: str) -> bool:
        """Check if location contains items with the specified SKU."""
        return self.sku_counts.get(sku, 0) > 0

    def add_items(self, sku: str, size: float, qty: int) -> None:
        """Add items to location inventory."""
        if qty <= 0:
            return
        if self.occupied + qty > self.capacity:
            raise ValueError(f"Adding {qty} items exceeds capacity ({self.capacity}) at {self.location_id}")
        self.sku_counts[sku] = self.sku_counts.get(sku, 0) + qty
        self.size_counts[size] = self.size_counts.get(size, 0) + qty

    def remove_items(self, sku: str, size: float, qty: int) -> None:
        """Remove items from location inventory."""
        if qty <= 0:
            return
        curr_sku = self.sku_counts.get(sku, 0)
        curr_size = self.size_counts.get(size, 0)
        if qty > curr_sku or qty > curr_size:
            raise ValueError(f"Cannot remove {qty} items of SKU {sku} from {self.location_id}")
        
        if curr_sku == qty:
            del self.sku_counts[sku]
        else:
            self.sku_counts[sku] = curr_sku - qty

        if curr_size == qty:
            del self.size_counts[size]
        else:
            self.size_counts[size] = curr_size - qty


class WarehouseState:
    """Central representation of the warehouse state across all locations."""

    def __init__(self, capacity_per_location: int = 18):
        self.capacity_per_location = capacity_per_location
        self.locations: Dict[str, LocationState] = {}

    def add_location(self, location_id: str, coordinates: Optional[Tuple[float, float, float]] = None) -> LocationState:
        loc = LocationState(location_id, capacity=self.capacity_per_location, coordinates=coordinates)
        self.locations[location_id] = loc
        return loc

    def get_location(self, location_id: str) -> LocationState:
        return self.locations[location_id]

    def total_locations(self) -> int:
        return len(self.locations)

    def total_occupied_units(self) -> int:
        return sum(loc.occupied for loc in self.locations.values())

    def total_capacity(self) -> int:
        return len(self.locations) * self.capacity_per_location

    def global_mixing_index(self) -> float:
        """Average Mixing Index across all locations."""
        if not self.locations:
            return 0.0
        return float(np.mean([loc.mixing_index() for loc in self.locations.values()]))

    def critical_locations_rate(self, threshold: float = 0.8) -> float:
        """Percentage of locations with Mixing Index > threshold."""
        if not self.locations:
            return 0.0
        critical = sum(1 for loc in self.locations.values() if loc.mixing_index() > threshold)
        return (critical / len(self.locations)) * 100.0

    def sku_dispersion(self, sku: str) -> float:
        """Proportion of locations storing this SKU over total locations."""
        if not self.locations:
            return 0.0
        count = sum(1 for loc in self.locations.values() if loc.has_sku(sku))
        return count / len(self.locations)

    def release_random_capacity(self, release_ratio: float = 0.20, seed: int = 42) -> List[Tuple[str, str, float]]:
        """Randomly empty approximately release_ratio of occupied slots to create initial free capacity."""
        rng = np.random.default_rng(seed)
        all_units: List[Tuple[str, str, float]] = []

        for loc_id, loc in self.locations.items():
            for sku, count in loc.sku_counts.items():
                # We associate with one of available sizes for removal
                sizes = [sz for sz, c in loc.size_counts.items() if c > 0]
                sz = sizes[0] if sizes else 9.0
                for _ in range(count):
                    all_units.append((loc_id, sku, sz))

        if not all_units:
            return []

        num_to_release = int(round(len(all_units) * release_ratio))
        indices_to_release = set(rng.choice(len(all_units), size=num_to_release, replace=False))

        released: List[Tuple[str, str, float]] = []
        for idx in indices_to_release:
            loc_id, sku, sz = all_units[idx]
            self.locations[loc_id].remove_items(sku, sz, 1)
            released.append((loc_id, sku, sz))

        return released

    @classmethod
    def from_long_dataframe(cls, long_df: pd.DataFrame, capacity: int = 18) -> "WarehouseState":
        """Instantiate and populate WarehouseState from normalized long dataframe."""
        state = cls(capacity_per_location=capacity)
        for loc_id, group in long_df.groupby("originalLocation"):
            loc = state.add_location(loc_id)
            for _, row in group.iterrows():
                ref = row.get("Reference")
                sz = row.get("size")
                if pd.notna(ref) and str(ref).strip():
                    size_val = float(sz) if pd.notna(sz) else 9.0
                    loc.add_items(str(ref).strip(), size_val, 1)
        return state
