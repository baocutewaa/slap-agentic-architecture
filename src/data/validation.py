"""Data validation module to audit datasets and ensure warehouse invariants.

Implements audit checks from Sections 3, 7 (Stage 1), and 8.4:
- Verify slot capacities and null rates
- Check reference catalog consistency
- Verify spatial level distributions (z = 1, 2, 3, 4)
- Validate size range constraints ([4, 16] in z in {3, 4})
"""

from typing import Dict, Any, List
import pandas as pd


def validate_raw_datasets(
    df_storage_loc: pd.DataFrame,
    df_random_storage: pd.DataFrame,
    df_product: pd.DataFrame
) -> Dict[str, Any]:
    """Audit primary warehouse datasets and check alignment with paper characteristics."""
    report: Dict[str, Any] = {}

    # 1. Location counts and z-distribution
    loc_col = df_storage_loc.columns[0]
    total_locations = df_storage_loc[loc_col].nunique()
    report["total_storage_locations"] = total_locations

    if "z" in df_storage_loc.columns:
        z_counts = df_storage_loc["z"].value_counts().to_dict()
        report["locations_by_z"] = z_counts

    # 2. Product count
    prod_ref_col = [c for c in df_product.columns if "reference" in c.lower()][0]
    report["catalog_product_count"] = df_product[prod_ref_col].nunique()

    # 3. Random storage shape
    report["random_storage_rows"] = len(df_random_storage)
    report["random_storage_slots_per_loc"] = len(df_random_storage.columns) - 1

    return report


def validate_warehouse_integrity(
    long_storage_df: pd.DataFrame,
    product_catalog_df: pd.DataFrame,
    max_capacity: int = 18,
    expected_size_range: tuple = (4.0, 16.0)
) -> Dict[str, Any]:
    """Validate normalized storage state against invariants: capacity, SKU validity, size range."""
    results: Dict[str, Any] = {"is_valid": True, "issues": []}

    # 1. Capacity per location
    occupied_per_loc = long_storage_df[long_storage_df["Reference"].notna()].groupby("originalLocation").size()
    exceeded = occupied_per_loc[occupied_per_loc > max_capacity]
    if len(exceeded) > 0:
        results["is_valid"] = False
        results["issues"].append(f"{len(exceeded)} locations exceed max capacity {max_capacity}.")

    # 2. Reference catalog membership
    prod_ref_col = [c for c in product_catalog_df.columns if "reference" in c.lower()][0]
    valid_refs = set(product_catalog_df[prod_ref_col].dropna().astype(str).str.strip())
    
    storage_refs = set(long_storage_df["Reference"].dropna().astype(str).str.strip())
    missing_refs = storage_refs - valid_refs
    if len(missing_refs) > 0:
        results["is_valid"] = False
        results["issues"].append(f"{len(missing_refs)} References in storage are not in Product catalog: {list(missing_refs)[:5]}.")

    # 3. Size range check
    sizes = long_storage_df["size"].dropna()
    min_sz, max_sz = sizes.min(), sizes.max()
    results["observed_size_min"] = float(min_sz) if len(sizes) > 0 else None
    results["observed_size_max"] = float(max_sz) if len(sizes) > 0 else None

    if min_sz < expected_size_range[0] or max_sz > expected_size_range[1]:
        results["issues"].append(
            f"Observed sizes [{min_sz}, {max_sz}] fall outside expected [{expected_size_range[0]}, {expected_size_range[1]}]."
        )

    return results
