"""Comprehensive Unit tests for Stage 1 Data Validation & Audit.

Reference: Sections 3, 7 (Stage 1), and 8.4 of SLAP-agentic-architecture Plan.md.
Validates:
- All 9 raw CSV loaders and delimiters
- Coordinate integrity and spatial level z distribution
- Storage slot parsing and 18-slot invariant
- Reference catalog consistency (Product vs Random Storage)
- Candidate scope (z in {3, 4}) size range [4.0, 16.0] and baseline MI
- Customer order and picking wave transaction constraints
- Storage policy snapshot discrepancies
"""

import pandas as pd
import pytest
from src.data.loaders import load_raw_csv, load_all_raw_datasets, CSV_DELIMITERS
from src.data.cleaning import (
    clean_storage_location,
    clean_product,
    clean_random_storage,
    parse_slot_value,
)
from src.data.validation import validate_warehouse_integrity
from src.data.audit import audit_scopes_and_baseline_mi
from src.model.warehouse_state import WarehouseState


def test_parse_slot_value():
    """Verify parsing slot strings 'Reference;Size'."""
    ref, sz = parse_slot_value("REF123;10.5")
    assert ref == "REF123"
    assert sz == 10.5

    ref_plain, sz_none = parse_slot_value("REF_PLAIN")
    assert ref_plain == "REF_PLAIN"
    assert sz_none is None

    empty_ref, empty_sz = parse_slot_value("")
    assert empty_ref is None
    assert empty_sz is None


def test_validate_warehouse_integrity_valid():
    """Verify clean dataset passes integrity checks."""
    long_df = pd.DataFrame([
        {"originalLocation": "LOC_1", "slot_id": 1, "Reference": "REF_A", "size": 8.0},
        {"originalLocation": "LOC_1", "slot_id": 2, "Reference": "REF_B", "size": 9.5},
    ])
    prod_df = pd.DataFrame({"Reference": ["REF_A", "REF_B", "REF_C"]})

    res = validate_warehouse_integrity(long_df, prod_df, max_capacity=18, expected_size_range=(4.0, 16.0))
    assert res["is_valid"] is True
    assert len(res["issues"]) == 0


def test_all_raw_files_loadable():
    """Verify all 9 raw warehouse CSV files are correctly loaded."""
    datasets = load_all_raw_datasets("data/raw")
    assert len(datasets) == len(CSV_DELIMITERS)
    for filename in CSV_DELIMITERS:
        assert filename in datasets
        assert len(datasets[filename]) > 0


def test_storage_location_structure_and_duplicate_coordinates():
    """Verify Storage_Location.csv has 2292 locations, expected z-counts, and duplicate coords."""
    df_loc = clean_storage_location(load_raw_csv("Storage_Location.csv"))
    assert len(df_loc) == 2292
    assert df_loc["originalLocation"].nunique() == 2292

    z_counts = df_loc["z"].value_counts().to_dict()
    assert z_counts[1] == 846
    assert z_counts[2] == 846
    assert z_counts[3] == 301
    assert z_counts[4] == 299

    coord_dups = df_loc[df_loc.duplicated(subset=["x", "y", "z"], keep=False)]
    assert len(coord_dups) == 2
    dup_locs = set(coord_dups["originalLocation"])
    assert dup_locs == {"K-23-30", "K-23-40"}


def test_product_catalog_integrity():
    """Verify Product.csv has 208 products, ABCCOD counts, and Sector PF."""
    df_prod = clean_product(load_raw_csv("Product.csv"))
    assert len(df_prod) == 208
    assert df_prod["Reference"].nunique() == 208

    abc_counts = df_prod["ABCCOD"].value_counts().to_dict()
    assert abc_counts == {"C": 94, "B": 70, "A": 44}
    assert set(df_prod["Sector"].unique()) == {"PF"}


def test_random_storage_slots_and_sku_catalog_match():
    """Verify Random_Storage.csv has 18 slots per location and 100% SKU match with Product catalog."""
    df_rand = load_raw_csv("Random_Storage.csv")
    assert len(df_rand) == 2292
    # 1 location column + 18 slot columns = 19
    assert len(df_rand.columns) == 19

    df_loc = load_raw_csv("Storage_Location.csv")
    df_prod = load_raw_csv("Product.csv")
    catalog_refs = set(df_prod["Reference"].astype(str).str.strip())

    long_df = clean_random_storage(df_rand, df_locations=df_loc)
    assert len(long_df) == 2292 * 18  # 41256 slots
    assert long_df["Reference"].isna().sum() == 0

    storage_refs = set(long_df["Reference"].dropna().astype(str).str.strip())
    assert len(storage_refs) == 208
    assert storage_refs == catalog_refs  # 100% match


def test_candidate_scope_z34_properties():
    """Verify Primary Candidate Scope (z in {3, 4}) satisfies all paper-alignment criteria."""
    df_rand = load_raw_csv("Random_Storage.csv")
    df_loc = load_raw_csv("Storage_Location.csv")
    long_df = clean_random_storage(df_rand, df_locations=df_loc, z_filter=[3, 4])

    # 600 locations, 10,800 slots
    assert long_df["originalLocation"].nunique() == 600
    assert len(long_df) == 600 * 18

    # Size range strictly between 4.0 and 16.0
    sizes = long_df["size"].dropna()
    assert float(sizes.min()) == 4.0
    assert float(sizes.max()) == 16.0

    # Baseline MI ~ 0.9136, Critical rate ~ 99.83%
    state = WarehouseState.from_long_dataframe(long_df, capacity=18)
    mi_vals = [loc.mixing_index() for loc in state.locations.values()]
    avg_mi = sum(mi_vals) / len(mi_vals)
    crit_pct = (sum(1 for m in mi_vals if m > 0.8) / len(mi_vals)) * 100.0

    assert 0.910 <= avg_mi <= 0.920
    assert 99.0 <= crit_pct <= 100.0


def test_customer_order_audit_metrics():
    """Verify Customer_Order.csv has 122,370 rows, 33 zero-quantities, and 16 missing sizes."""
    df_order = load_raw_csv("Customer_Order.csv")
    assert len(df_order) == 122370
    assert df_order["orderNumber"].nunique() == 32634
    assert df_order["waveNumber"].nunique() == 9784

    qty_col = [c for c in df_order.columns if "quantity" in c.lower()][0]
    zero_or_neg = (df_order[qty_col] <= 0).sum()
    assert zero_or_neg == 33
    assert df_order["Size (US)"].isna().sum() == 16


def test_picking_wave_single_unit_invariant():
    """Verify Picking_Wave.csv has 215,192 rows and all quantityToPick values are 1."""
    df_pick = load_raw_csv("Picking_Wave.csv")
    assert len(df_pick) == 215192
    pick_qty_col = [c for c in df_pick.columns if "quantity" in c.lower()][0]
    assert set(df_pick[pick_qty_col].unique()) == {1}


def test_policy_storage_extra_entities():
    """Verify extra locations in Dedicated/Hybrid (+48) and Class_Based (+49, +109 SKUs)."""
    df_rand = load_raw_csv("Random_Storage.csv")
    rand_locs = set(df_rand.iloc[:, 0].astype(str).str.strip())

    df_ded = load_raw_csv("Dedicated_Storage.csv")
    ded_locs = set(df_ded.iloc[:, 0].astype(str).str.strip())
    assert len(ded_locs - rand_locs) == 48

    df_hyb = load_raw_csv("Hybrid_Storage.csv")
    hyb_locs = set(df_hyb.iloc[:, 0].astype(str).str.strip())
    assert len(hyb_locs - rand_locs) == 48

    df_cls = load_raw_csv("Class_Based_Storage.csv")
    cls_locs = set(df_cls.iloc[:, 0].astype(str).str.strip())
    assert len(cls_locs - rand_locs) == 49
