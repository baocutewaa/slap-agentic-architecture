"""Comparative experiment orchestrator running Heuristic, Supervised, and Adaptive modes.

Reference: Sections 1.1, 1.2, and 7 (Stage 6) of the plan:
Ensures all 3 modes run on the exact same initial warehouse state and identical event stream.
"""

from typing import Dict, Any, List
import copy
import pandas as pd

from src.model.warehouse_state import WarehouseState
from src.agents.heuristic_agent import HeuristicAgent
from src.agents.supervised_agent import SupervisedAgent
from src.agents.adaptive_agent import AdaptiveAgent
from src.simulation.runner import SimulationRunner


def run_comparative_experiment(
    initial_state: WarehouseState,
    events: List[Dict[str, Any]],
    config: Dict[str, Any],
    output_dir: str = "outputs"
) -> Dict[str, Any]:
    """Run all three progressive autonomy agents under identical conditions."""
    results: Dict[str, Any] = {}

    # 1. Instantiate agents from config
    heur_cfg = config.get("heuristic", {})
    sup_cfg = config.get("supervised", {})
    adapt_cfg = config.get("adaptive", {})

    agents = [
        HeuristicAgent(
            gamma=heur_cfg.get("gamma", 0.1),
            tau=heur_cfg.get("tau", 0.90),
            top_k=heur_cfg.get("top_k_candidates", 10)
        ),
        SupervisedAgent(
            gamma=sup_cfg.get("gamma", 0.1),
            tau=sup_cfg.get("tau", 0.90),
            top_k=sup_cfg.get("top_k_candidates", 10),
            auto_approval_rule=sup_cfg.get("auto_approval_rule", "delta_mi_le_zero"),
            operator_fallback=sup_cfg.get("operator_fallback", "pending_manual")
        ),
        AdaptiveAgent(
            learning_rate_eta=adapt_cfg.get("learning_rate_eta", 0.05),
            regularization_lambda=adapt_cfg.get("regularization_lambda", 0.01),
            epsilon_exploration=adapt_cfg.get("epsilon_exploration", 0.1),
            tau=adapt_cfg.get("tau", 0.90),
            top_k=adapt_cfg.get("top_k_candidates", 10),
            reward_mode=adapt_cfg.get("reward_mode", "global_mi_delta"),
            seed=config.get("simulation", {}).get("seed", 42)
        )
    ]

    for agent in agents:
        runner = SimulationRunner(
            agent=agent,
            initial_state=initial_state,
            events=events,
            snapshot_interval=100,
            output_dir=output_dir
        )
        logger = runner.run()
        results[agent.mode_name] = {
            "action_logs": logger.action_logs,
            "metric_snapshots": logger.metric_snapshots
        }

    return results
