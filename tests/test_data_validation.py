"""Unit tests for data validation logic.

Reference: Sections 3.2, 7 (Stage 1), and 8.4 of the Plan.
"""

import pandas as pd
from src.data.validation import validate_warehouse_integrity
from src.data.cleaning import parse_slot_value


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
