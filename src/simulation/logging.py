"""Logging and recording utilities for simulation runs.

Captures per-event ActionLogs, periodic warehouse metric snapshots, and runtime stats.
Reference: Section 5.1 of the plan.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import json
import pandas as pd

from src.agents.base_agent import ActionDecision


class SimulationLogger:
    """Manages logs, decisions, and trajectory metrics during simulation."""

    def __init__(self, agent_name: str, output_dir: Union[str, Path] = "outputs"):
        self.agent_name = agent_name
        self.output_dir = Path(output_dir)
        self.action_logs: List[Dict[str, Any]] = []
        self.metric_snapshots: List[Dict[str, Any]] = []

    def record_decision(self, decision: ActionDecision) -> None:
        """Record an individual event action decision."""
        rec = {
            "event_id": decision.event_id,
            "agent_mode": decision.agent_mode,
            "sku": decision.sku,
            "size": decision.size,
            "quantity": decision.quantity,
            "status": decision.status,
            "reason": decision.reason,
            "allocations": (
                str(decision.selected_allocation.allocations)
                if decision.selected_allocation is not None else ""
            ),
            "is_split": (
                decision.selected_allocation.is_split
                if decision.selected_allocation is not None else False
            ),
            "mi_before": decision.mi_before,
            "mi_after": decision.mi_after,
            "delta_mi": decision.delta_mi,
            "utility": decision.utility,
            "runtime_ms": decision.runtime_ms,
        }
        if decision.weights_after is not None:
            rec["weights_after"] = json.dumps(decision.weights_after)

        self.action_logs.append(rec)

    def record_snapshot(self, event_idx: int, metrics: Dict[str, Any]) -> None:
        """Record a periodic metric snapshot (e.g. at every step or every 100 steps)."""
        snapshot = {"event_id": event_idx, "agent_mode": self.agent_name, **metrics}
        self.metric_snapshots.append(snapshot)

    def export(self) -> Tuple[Path, Path]:
        """Export action logs and metric curves to outputs directory."""
        logs_dir = self.output_dir / "logs"
        metrics_dir = self.output_dir / "metrics"
        logs_dir.mkdir(parents=True, exist_ok=True)
        metrics_dir.mkdir(parents=True, exist_ok=True)

        actions_csv = logs_dir / f"actions_{self.agent_name}.csv"
        metrics_csv = metrics_dir / f"metrics_{self.agent_name}.csv"

        if self.action_logs:
            pd.DataFrame(self.action_logs).to_csv(actions_csv, index=False)
        if self.metric_snapshots:
            pd.DataFrame(self.metric_snapshots).to_csv(metrics_csv, index=False)

        return actions_csv, metrics_csv
