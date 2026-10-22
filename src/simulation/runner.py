"""Simulation runner for an individual agent across the event stream.

Reference: Section 7 (Stage 6) of the plan.
"""

from typing import Dict, Any, Optional
import copy
from tqdm import tqdm

from src.agents.base_agent import BaseAgent
from src.model.warehouse_state import WarehouseState
from src.model.metrics import calculate_warehouse_metrics
from src.simulation.logging import SimulationLogger


class SimulationRunner:
    """Executes an agent against a sequence of inbound events on an initial warehouse state."""

    def __init__(
        self,
        agent: BaseAgent,
        initial_state: WarehouseState,
        events: list,
        snapshot_interval: int = 100,
        output_dir: str = "outputs"
    ):
        self.agent = agent
        # Deepcopy state so multiple runs start from the identical initial released configuration
        self.state = copy.deepcopy(initial_state)
        self.events = events
        self.snapshot_interval = snapshot_interval
        self.logger = SimulationLogger(agent.mode_name, output_dir=output_dir)

    def run(self, show_progress: bool = True) -> SimulationLogger:
        """Run the simulation loop across all events."""
        # Initial snapshot before processing any inbound event
        init_metrics = calculate_warehouse_metrics(self.state)
        self.logger.record_snapshot(0, init_metrics)

        iterator = tqdm(self.events, desc=f"Simulating {self.agent.mode_name}") if show_progress else self.events

        for idx, event in enumerate(iterator, start=1):
            decision = self.agent.process_event(event, self.state)
            self.logger.record_decision(decision)

            if idx % self.snapshot_interval == 0 or idx == len(self.events):
                current_metrics = calculate_warehouse_metrics(self.state)
                self.logger.record_snapshot(idx, current_metrics)

        self.logger.export()
        return self.logger
