"""Data loaders for warehouse CSV datasets.

Handles file encodings, delimiters, and file discovery according to Section 3.2 of the plan:
- Random_Storage and Storage_Location: comma delimiter (,)
- Product, Customer_Order, Picking_Wave, Storage Policies: semicolon delimiter (;)
- Support_Points_Navigation: semicolon delimiter (;)
"""

import os
from pathlib import Path
from typing import Dict, Optional, Union
import pandas as pd

# Standard file delimiter registry based on audit
CSV_DELIMITERS: Dict[str, str] = {
    "Storage_Location.csv": ",",
    "Random_Storage.csv": ",",
    "Product.csv": ";",
    "Customer_Order.csv": ";",
    "Picking_Wave.csv": ";",
    "Class_Based_Storage.csv": ";",
    "Dedicated_Storage.csv": ";",
    "Hybrid_Storage.csv": ";",
    "Support_Points_Navigation.csv": ";",
}


def get_raw_file_path(filename: str, raw_dir: Union[str, Path] = "data/raw") -> Path:
    """Resolve file path in raw directory, handling possible suffix variations like (1)."""
    raw_path = Path(raw_dir)
    primary = raw_path / filename
    if primary.exists():
        return primary
    
    # Try alternate name with (1) if not found
    stem, ext = os.path.splitext(filename)
    alternate = raw_path / f"{stem}(1){ext}"
    if alternate.exists():
        return alternate

    raise FileNotFoundError(f"Neither {primary} nor {alternate} was found in {raw_dir}.")


def load_raw_csv(
    filename: str,
    raw_dir: Union[str, Path] = "data/raw",
    delimiter: Optional[str] = None,
    encoding: str = "utf-8",
    **kwargs
) -> pd.DataFrame:
    """Load a raw warehouse CSV file with proper delimiter and encoding."""
    file_path = get_raw_file_path(filename, raw_dir)
    delim = delimiter or CSV_DELIMITERS.get(filename, ",")

    try:
        df = pd.read_csv(file_path, delimiter=delim, encoding=encoding, **kwargs)
    except UnicodeDecodeError:
        # Fallback to latin-1 if utf-8 fails
        df = pd.read_csv(file_path, delimiter=delim, encoding="latin-1", **kwargs)
    return df
