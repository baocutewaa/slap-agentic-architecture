"""Warehouse state representation and state management.

Tracks location inventories, free capacity, sizes, coordinates, and slot-level items.
Supports releasing ~20% initial capacity reproducibly and atomic allocation updates.
Reference: Section 2.1, 4.4, 5.1, and 8.2 of the Plan.
"""

from typing import Dict, List, Optional, Tuple, Set, Any
import numpy as np
import pandas as pd


class LocationState:
    """State of an individual storage location with 18 slots."""

    def __init__(
        self,
        location_id: str,
        capacity: int = 18,
        coordinates: Optional[Tuple[float, float, float]] = None
    ):
        self.location_id = str(location_id).strip()
        self.capacity = capacity
        self.coordinates = coordinates or (0.0, 0.0, 0.0)
        self.slots: Dict[int, Optional[Tuple[str, float]]] = {i: None for i in range(1, capacity + 1)}
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

    def is_critical(self, threshold: float = 0.8) -> bool:
        """Check if location has high mixing index exceeding threshold."""
        return self.mixing_index() > threshold

    def has_size(self, size: float) -> bool:
        """Check if location contains items with the specified size."""
        return self.size_counts.get(float(size), 0) > 0

    def has_sku(self, sku: str) -> bool:
        """Check if location contains items with the specified SKU."""
        return self.sku_counts.get(str(sku).strip(), 0) > 0

    def add_items(self, sku: str, size: float, qty: int = 1, slot_id: Optional[int] = None) -> None:
        """Add items to location inventory, assigning to slots."""
        if qty <= 0:
            return
        if self.occupied + qty > self.capacity:
            raise ValueError(
                f"Adding {qty} items exceeds capacity ({self.capacity}) at {self.location_id} (occupied: {self.occupied})"
            )
        sku_clean = str(sku).strip()
        size_clean = float(size)

        for _ in range(qty):
            # Target specific slot if requested and free
            if slot_id is not None and slot_id in self.slots and self.slots[slot_id] is None:
                target_slot = slot_id
                slot_id = None
            else:
                target_slot = next(
                    s for s in range(1, self.capacity + 1) if self.slots[s] is None
                )
            self.slots[target_slot] = (sku_clean, size_clean)
            self.sku_counts[sku_clean] = self.sku_counts.get(sku_clean, 0) + 1
            self.size_counts[size_clean] = self.size_counts.get(size_clean, 0) + 1

    def remove_items(self, sku: str, size: float, qty: int = 1, slot_id: Optional[int] = None) -> None:
        """Remove items from location inventory."""
        if qty <= 0:
            return
        sku_clean = str(sku).strip()
        size_clean = float(size)

        curr_sku = self.sku_counts.get(sku_clean, 0)
        curr_size = self.size_counts.get(size_clean, 0)
        if qty > curr_sku or qty > curr_size:
            raise ValueError(
                f"Cannot remove {qty} items of SKU {sku_clean} (size {size_clean}) from {self.location_id}"
            )

        for _ in range(qty):
            if slot_id is not None and self.slots.get(slot_id) == (sku_clean, size_clean):
                target_slot = slot_id
                slot_id = None
            else:
                # Find matching slot
                matching_slots = [
                    s for s, item in self.slots.items() if item == (sku_clean, size_clean)
                ]
                if matching_slots:
                    target_slot = matching_slots[0]
                else:
                    # Fallback to any slot with this SKU if exact pair not bound
                    sku_slots = [
                        s for s, item in self.slots.items() if item is not None and item[0] == sku_clean
                    ]
                    target_slot = sku_slots[0] if sku_slots else next(
                        s for s, item in self.slots.items() if item is not None
                    )

            self.slots[target_slot] = None
            self.sku_counts[sku_clean] -= 1
            if self.sku_counts[sku_clean] == 0:
                del self.sku_counts[sku_clean]
            self.size_counts[size_clean] -= 1
            if self.size_counts[size_clean] == 0:
                del self.size_counts[size_clean]

    def remove_slot(self, slot_id: int) -> Optional[Tuple[str, float]]:
        """Empty a specific slot and update SKU and size counts."""
        item = self.slots.get(slot_id)
        if item is None:
            return None
        sku, sz = item
        self.slots[slot_id] = None

        self.sku_counts[sku] -= 1
        if self.sku_counts[sku] == 0:
            del self.sku_counts[sku]

        self.size_counts[sz] -= 1
        if self.size_counts[sz] == 0:
            del self.size_counts[sz]

        return item


class WarehouseState:
    """Central representation of the warehouse state across all locations."""

    def __init__(self, capacity_per_location: int = 18):
        self.capacity_per_location = capacity_per_location
        self.locations: Dict[str, LocationState] = {}

    def add_location(
        self,
        location_id: str,
        coordinates: Optional[Tuple[float, float, float]] = None
    ) -> LocationState:
        loc_id = str(location_id).strip()
        loc = LocationState(loc_id, capacity=self.capacity_per_location, coordinates=coordinates)
        self.locations[loc_id] = loc
        return loc

    def get_location(self, location_id: str) -> LocationState:
        return self.locations[str(location_id).strip()]

    def total_locations(self) -> int:
        return len(self.locations)

    def total_occupied_units(self) -> int:
        return sum(loc.occupied for loc in self.locations.values())

    def total_capacity(self) -> int:
        return len(self.locations) * self.capacity_per_location

    def occupancy_rate(self) -> float:
        """Percentage of total warehouse capacity currently occupied."""
        cap = self.total_capacity()
        return (self.total_occupied_units() / cap * 100.0) if cap > 0 else 0.0

    def free_capacity(self) -> int:
        """Total unoccupied slots across warehouse."""
        return max(0, self.total_capacity() - self.total_occupied_units())

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
        clean_sku = str(sku).strip()
        count = sum(1 for loc in self.locations.values() if loc.has_sku(clean_sku))
        return count / len(self.locations)

    def release_random_capacity(
        self,
        release_ratio: float = 0.20,
        seed: int = 42
    ) -> List[Tuple[str, int, str, float]]:
        """Randomly empty approximately release_ratio of occupied slots across the warehouse.
        
        Returns a list of released slot records: (location_id, slot_id, sku, size).
        """
        rng = np.random.default_rng(seed)
        all_occupied: List[Tuple[str, int, str, float]] = []

        for loc_id, loc in self.locations.items():
            for slot_id, item in loc.slots.items():
                if item is not None:
                    sku, sz = item
                    all_occupied.append((loc_id, slot_id, sku, sz))

        if not all_occupied:
            return []

        num_to_release = int(round(len(all_occupied) * release_ratio))
        chosen_indices = rng.choice(len(all_occupied), size=num_to_release, replace=False)

        released: List[Tuple[str, int, str, float]] = []
        for idx in chosen_indices:
            loc_id, slot_id, sku, sz = all_occupied[idx]
            self.locations[loc_id].remove_slot(slot_id)
            released.append((loc_id, slot_id, sku, sz))

        return released

    def apply_allocation(self, sku: str, size: float, allocations: List[Tuple[str, int]]) -> None:
        """Apply an allocation atomically to the warehouse state.
        
        Rolls back if any location cannot accept the allocation.
        """
        applied: List[Tuple[str, int]] = []
        try:
            for loc_id, qty in allocations:
                loc = self.get_location(loc_id)
                loc.add_items(sku, size, qty)
                applied.append((loc_id, qty))
        except Exception as e:
            # Rollback applied partial allocations
            for loc_id, qty in applied:
                self.get_location(loc_id).remove_items(sku, size, qty)
            raise e

    def to_location_dataframe(self) -> pd.DataFrame:
        """Export state summary per location to a DataFrame."""
        records = []
        for loc_id, loc in self.locations.items():
            records.append({
                "originalLocation": loc_id,
                "x": loc.coordinates[0],
                "y": loc.coordinates[1],
                "z": loc.coordinates[2],
                "capacity": loc.capacity,
                "occupied": loc.occupied,
                "free_capacity": loc.free_capacity,
                "mixing_index": round(loc.mixing_index(), 4),
                "is_critical": loc.is_critical(),
                "sku_count": len(loc.sku_counts),
                "distinct_sizes_count": len(loc.size_counts),
            })
        return pd.DataFrame(records)

    def to_slot_dataframe(self) -> pd.DataFrame:
        """Export detailed state of all individual slots to a DataFrame."""
        records = []
        for loc_id, loc in self.locations.items():
            for slot_id in range(1, loc.capacity + 1):
                item = loc.slots.get(slot_id)
                records.append({
                    "originalLocation": loc_id,
                    "slot_id": slot_id,
                    "Reference": item[0] if item is not None else None,
                    "size": item[1] if item is not None else None,
                    "is_occupied": item is not None,
                    "x": loc.coordinates[0],
                    "y": loc.coordinates[1],
                    "z": loc.coordinates[2],
                })
        return pd.DataFrame(records)

    @classmethod
    def from_long_dataframe(
        cls,
        long_df: pd.DataFrame,
        capacity: int = 18,
        df_locations: Optional[pd.DataFrame] = None
    ) -> "WarehouseState":
        """Instantiate and populate WarehouseState from normalized long dataframe."""
        state = cls(capacity_per_location=capacity)

        # Build coordinate lookup if provided
        coord_map = {}
        if df_locations is not None:
            for _, r in df_locations.iterrows():
                loc = str(r["originalLocation"]).strip()
                coord_map[loc] = (float(r.get("x", 0.0)), float(r.get("y", 0.0)), float(r.get("z", 0.0)))

        for loc_id, group in long_df.groupby("originalLocation"):
            clean_id = str(loc_id).strip()
            # Try coordinates from group columns or coord_map
            first_row = group.iloc[0]
            if "x" in group.columns and "y" in group.columns and "z" in group.columns:
                coords = (
                    float(first_row.get("x", 0.0) or 0.0),
                    float(first_row.get("y", 0.0) or 0.0),
                    float(first_row.get("z", 0.0) or 0.0),
                )
            else:
                coords = coord_map.get(clean_id, (0.0, 0.0, 0.0))

            loc = state.add_location(clean_id, coordinates=coords)

            for _, row in group.iterrows():
                ref = row.get("Reference")
                sz = row.get("size")
                slot_id = row.get("slot_id")
                if pd.notna(ref) and str(ref).strip():
                    size_val = float(sz) if pd.notna(sz) else 9.0
                    slot_int = int(slot_id) if pd.notna(slot_id) else None
                    loc.add_items(str(ref).strip(), size_val, qty=1, slot_id=slot_int)

        return state
