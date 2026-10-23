"""Data cleaning and transformation module.

Implements data cleaning rules from Section 3.2:
- Whitespace trimming for strings (originalLocation, Reference, etc.)
- Parsing 18 slot columns into normalized long format (location, slot, reference, size)
- Numeric conversion of coordinates and quantities
- Scope filtering (e.g. z in {3, 4})
"""

from typing import List, Optional, Tuple
import pandas as pd


def clean_storage_location(df: pd.DataFrame) -> pd.DataFrame:
    """Clean Storage_Location dataframe: trim identifiers and convert x, y, z to numeric."""
    clean_df = df.copy()
    for col in ["originalLocation", "position"]:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].astype(str).str.strip()

    for col in ["x", "y", "z"]:
        if col in clean_df.columns:
            clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce")

    return clean_df


def clean_product(df: pd.DataFrame) -> pd.DataFrame:
    """Clean Product catalog: trim strings, normalize Reference and categories."""
    clean_df = df.copy()
    for col in clean_df.select_dtypes(include="object").columns:
        clean_df[col] = clean_df[col].astype(str).str.strip()
    return clean_df


def parse_slot_value(val: str) -> Tuple[Optional[str], Optional[float]]:
    """Parse slot string in format 'Reference;Size' into (reference, size)."""
    if pd.isna(val) or not str(val).strip():
        return None, None
    s = str(val).strip()
    if ";" in s:
        parts = s.rsplit(";", 1)
        ref = parts[0].strip()
        try:
            size = float(parts[1].strip())
        except (ValueError, TypeError):
            size = None
        return ref, size
    return s, None


def clean_random_storage(
    df_random: pd.DataFrame,
    df_locations: Optional[pd.DataFrame] = None,
    z_filter: Optional[List[int]] = None
) -> pd.DataFrame:
    """Transform wide Random_Storage (2292 locations x 18 slot columns) into long format.
    
    Returns a dataframe with columns:
        ['originalLocation', 'slot_id', 'Reference', 'size', 'z']
    """
    df = df_random.copy()
    first_col = df.columns[0]
    df.rename(columns={first_col: "originalLocation"}, inplace=True)
    df["originalLocation"] = df["originalLocation"].astype(str).str.strip()

    # Identify slot columns (remaining 18 columns)
    slot_cols = [c for c in df.columns if c != "originalLocation"]

    long_records = []
    for _, row in df.iterrows():
        loc = row["originalLocation"]
        for idx, col in enumerate(slot_cols, start=1):
            val = row[col]
            ref, size = parse_slot_value(val)
            long_records.append({
                "originalLocation": loc,
                "slot_id": idx,
                "Reference": ref,
                "size": size
            })

    long_df = pd.DataFrame(long_records)

    # Attach coordinates (x, y, z) if locations dataframe is provided
    if df_locations is not None:
        loc_clean = clean_storage_location(df_locations)
        loc_clean_dedup = loc_clean.drop_duplicates(subset=["originalLocation"])
        loc_map = loc_clean_dedup.set_index("originalLocation")[["x", "y", "z"]].to_dict(orient="index")
        
        long_df["x"] = long_df["originalLocation"].map(lambda l: loc_map.get(l, {}).get("x"))
        long_df["y"] = long_df["originalLocation"].map(lambda l: loc_map.get(l, {}).get("y"))
        long_df["z"] = long_df["originalLocation"].map(lambda l: loc_map.get(l, {}).get("z"))

        if z_filter is not None:
            long_df = long_df[long_df["z"].isin(z_filter)].copy()

    return long_df


def save_normalized_snapshots(
    raw_dir: str = "data/raw",
    interim_dir: str = "data/interim"
) -> dict:
    """Save normalized long-format storage snapshots into interim directory.
    
    Generates:
    - random_storage_long_all.csv (all 2292 locations)
    - random_storage_long_z34.csv (primary scope: z in {3, 4}, 600 locations)
    - random_storage_long_z3.csv (sensitivity: z=3, 301 locations)
    - random_storage_long_z4.csv (sensitivity: z=4, 299 locations)
    """
    from pathlib import Path
    from src.data.loaders import load_raw_csv

    out_path = Path(interim_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    df_loc = load_raw_csv("Storage_Location.csv", raw_dir=raw_dir)
    df_rand = load_raw_csv("Random_Storage.csv", raw_dir=raw_dir)

    outputs = {}
    scopes = {
        "all": None,
        "z34": [3, 4],
        "z3": [3],
        "z4": [4],
    }

    for name, z_filter in scopes.items():
        long_df = clean_random_storage(df_rand, df_locations=df_loc, z_filter=z_filter)
        file_path = out_path / f"random_storage_long_{name}.csv"
        long_df.to_csv(file_path, index=False)
        outputs[name] = file_path

    return outputs



def clean_customer_order(df: pd.DataFrame) -> pd.DataFrame:
    """Clean Customer_Order records: trim text columns, drop <=0 quantities, convert numeric."""
    clean_df = df.copy()
    for col in clean_df.select_dtypes(include="object").columns:
        clean_df[col] = clean_df[col].astype(str).str.strip()

    qty_col = [c for c in clean_df.columns if "quantity" in c.lower()]
    if qty_col:
        col_name = qty_col[0]
        clean_df[col_name] = pd.to_numeric(clean_df[col_name], errors="coerce").fillna(0)
        clean_df = clean_df[clean_df[col_name] > 0].copy()

    return clean_df
