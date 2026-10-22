"""Inbound event stream generator.

Generates 10,000 inbound events according to Section 4 of the Plan:
- SKU i_t: sampled proportionally to stock frequency in the primary scope (z in {3, 4})
- Size s_t: sampled conditionally based on observed sizes of that SKU
- Quantity u_t: sampled from empirical positive quantities in Customer_Order
- Fixed random seed for complete reproducibility across all agent modes
"""

from pathlib import Path
from typing import Optional, Union, Dict, List
import numpy as np
import pandas as pd


def generate_inbound_stream(
    long_storage_df: pd.DataFrame,
    customer_order_df: pd.DataFrame,
    num_events: int = 10000,
    seed: int = 42,
    output_path: Optional[Union[str, Path]] = None
) -> pd.DataFrame:
    """Generate reproducible inbound event stream.
    
    Each record represents: (event_id, reference, size, quantity).
    """
    rng = np.random.default_rng(seed)

    # 1. Calculate stock frequency of each SKU (Reference)
    stock_records = long_storage_df[long_storage_df["Reference"].notna()].copy()
    sku_counts = stock_records["Reference"].value_counts()
    skus = sku_counts.index.to_numpy()
    sku_probs = (sku_counts / sku_counts.sum()).to_numpy()

    # 2. Build conditional size distributions per SKU
    sku_to_sizes: Dict[str, np.ndarray] = {}
    for ref, group in stock_records.groupby("Reference"):
        valid_sizes = group["size"].dropna().to_numpy()
        if len(valid_sizes) > 0:
            sku_to_sizes[ref] = valid_sizes
        else:
            sku_to_sizes[ref] = np.array([9.0])  # fallback median size if missing

    # 3. Extract empirical positive quantities from Customer_Order
    qty_col = [c for c in customer_order_df.columns if "quantity" in c.lower()][0]
    valid_quantities = customer_order_df[qty_col].dropna().to_numpy()
    valid_quantities = valid_quantities[valid_quantities > 0]
    if len(valid_quantities) == 0:
        valid_quantities = np.array([1, 2, 3, 4, 6, 8, 12, 18])

    # 4. Generate events
    sampled_skus = rng.choice(skus, size=num_events, p=sku_probs)
    sampled_quantities = rng.choice(valid_quantities, size=num_events)

    events: List[Dict] = []
    for i in range(num_events):
        sku = sampled_skus[i]
        possible_sizes = sku_to_sizes.get(sku, np.array([9.0]))
        size = float(rng.choice(possible_sizes))
        qty = int(sampled_quantities[i])
        
        events.append({
            "event_id": i + 1,
            "reference": sku,
            "size": size,
            "quantity": qty
        })

    events_df = pd.DataFrame(events)

    if output_path is not None:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        events_df.to_csv(out_p, index=False)

    return events_df
