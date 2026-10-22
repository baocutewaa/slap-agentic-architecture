"""Comparative tables and summary metrics generation.

Produces tables matching Section 1.2 and Section 9.1:
- Mode (Baseline - Random, Heuristic, Supervised, Adaptive)
- Final Average Mixing Index
- Locations with MI > 0.8 (%)
- Cumulative executed actions
- Execution rate (%)
"""

from pathlib import Path
from typing import Dict, Any, List, Union
import pandas as pd


def generate_comparison_table(
    experiment_results: Dict[str, Any],
    baseline_mi: float,
    baseline_critical_pct: float,
    total_events: int = 10000
) -> pd.DataFrame:
    """Compile final metrics summary table across Baseline and all agent modes."""
    rows: List[Dict[str, Any]] = [
        {
            "Configuration": "Baseline - Random",
            "Average_MI_Final": baseline_mi,
            "Critical_Locations_Pct": baseline_critical_pct,
            "Cumulative_Executed_Actions": 0,
            "Execution_Rate_Pct": 0.0
        }
    ]

    for mode_name, data in experiment_results.items():
        snapshots = data.get("metric_snapshots", [])
        actions = data.get("action_logs", [])

        final_snapshot = snapshots[-1] if snapshots else {}
        final_mi = final_snapshot.get("average_mi", 0.0)
        critical_pct = final_snapshot.get("critical_locations_pct", 0.0)

        executed_count = sum(1 for a in actions if a.get("status") == "executed")
        exec_rate = (executed_count / total_events) * 100.0 if total_events > 0 else 0.0

        rows.append({
            "Configuration": mode_name.capitalize(),
            "Average_MI_Final": round(final_mi, 4),
            "Critical_Locations_Pct": round(critical_pct, 2),
            "Cumulative_Executed_Actions": executed_count,
            "Execution_Rate_Pct": round(exec_rate, 2)
        })

    return pd.DataFrame(rows)


def export_summary_table(
    df: pd.DataFrame,
    output_path: Union[str, Path] = "outputs/tables/table_final_metrics.csv"
) -> Path:
    """Export summary metrics table to CSV."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    return p
