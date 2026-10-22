"""Visualization module for simulation results.

Generates the required figures from Section 9.3:
- fig_mi_over_time.png: Average MI progression over 10,000 events
- fig_cumulative_actions.png: Cumulative executed actions
- fig_critical_locations.png: Rate of critical locations (MI > 0.8)
"""

from pathlib import Path
from typing import Dict, Any, Union
import matplotlib.pyplot as plt
import pandas as pd


def plot_mi_curves(
    experiment_results: Dict[str, Any],
    baseline_mi: float,
    output_path: Union[str, Path] = "outputs/figures/fig_mi_over_time.png"
) -> Path:
    """Plot Average Mixing Index curves across events for all configurations."""
    plt.figure(figsize=(10, 6))

    for mode_name, data in experiment_results.items():
        snapshots = data.get("metric_snapshots", [])
        if snapshots:
            df = pd.DataFrame(snapshots)
            plt.plot(df["event_id"], df["average_mi"], label=mode_name.capitalize(), linewidth=2)

    plt.axhline(y=baseline_mi, color="gray", linestyle="--", label="Baseline (Random)")
    plt.title("Average Mixing Index Progression over Inbound Events", fontsize=14)
    plt.xlabel("Event Number", fontsize=12)
    plt.ylabel("Average Mixing Index (MI)", fontsize=12)
    plt.legend(fontsize=11)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_p, dpi=300)
    plt.close()
    return out_p


def plot_cumulative_actions(
    experiment_results: Dict[str, Any],
    output_path: Union[str, Path] = "outputs/figures/fig_cumulative_actions.png"
) -> Path:
    """Plot cumulative executed actions over event sequence."""
    plt.figure(figsize=(10, 6))

    for mode_name, data in experiment_results.items():
        actions = data.get("action_logs", [])
        if actions:
            df = pd.DataFrame(actions)
            df["is_executed"] = (df["status"] == "executed").astype(int)
            df["cumulative_executed"] = df["is_executed"].cumsum()
            plt.plot(df["event_id"], df["cumulative_executed"], label=mode_name.capitalize(), linewidth=2)

    plt.title("Cumulative Executed Actions over Inbound Events", fontsize=14)
    plt.xlabel("Event Number", fontsize=12)
    plt.ylabel("Cumulative Executed Actions", fontsize=12)
    plt.legend(fontsize=11)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_p, dpi=300)
    plt.close()
    return out_p


def plot_critical_rate_curves(
    experiment_results: Dict[str, Any],
    baseline_critical_pct: float,
    output_path: Union[str, Path] = "outputs/figures/fig_critical_locations.png"
) -> Path:
    """Plot percentage of locations with MI > 0.8 over events."""
    plt.figure(figsize=(10, 6))

    for mode_name, data in experiment_results.items():
        snapshots = data.get("metric_snapshots", [])
        if snapshots:
            df = pd.DataFrame(snapshots)
            plt.plot(df["event_id"], df["critical_locations_pct"], label=mode_name.capitalize(), linewidth=2)

    plt.axhline(y=baseline_critical_pct, color="gray", linestyle="--", label="Baseline (Random)")
    plt.title("Critical Locations Percentage (MI > 0.8)", fontsize=14)
    plt.xlabel("Event Number", fontsize=12)
    plt.ylabel("Locations with MI > 0.8 (%)", fontsize=12)
    plt.legend(fontsize=11)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_p, dpi=300)
    plt.close()
    return out_p
