"""Test verification for all phase deliverables from Phase 1 through Phase 5.

Verifies that every phase satisfies complete deliverables in:
- outputs/figures/
- outputs/tables/
- outputs/metrics/
- outputs/logs/
- outputs/reports/
"""

from pathlib import Path
import pytest
import pandas as pd


@pytest.fixture
def outputs_dir():
    return Path("outputs")


def test_all_reports_exist(outputs_dir):
    """Verify that all 5 phase technical reports exist and are non-empty."""
    reports = [
        "phase1_data_audit.md",
        "phase2_state_report.md",
        "phase3_event_generator_report.md",
        "phase4_allocation_engine_report.md",
        "phase5_agents_report.md"
    ]
    for r in reports:
        p = outputs_dir / "reports" / r
        assert p.exists(), f"Report {r} does not exist!"
        assert p.stat().st_size > 1000, f"Report {r} is too short or empty!"


def test_all_figures_exist(outputs_dir):
    """Verify that required figures exist for all phases with publication quality."""
    expected_figures = {
        "phase1": [
            "phase1_warehouse_layout_z_distribution.png",
            "phase1_baseline_mi_distribution.png",
            "phase1_sku_pareto_analysis.png",
            "phase1_storage_policy_comparison.png"
        ],
        "phase2": [
            "phase2_capacity_release_distribution.png",
            "phase2_mi_before_after_release.png",
            "phase2_spatial_occupancy_map.png",
            "phase2_sensitivity_scopes_mi.png"
        ],
        "phase3": [
            "phase3_sku_frequency_empirical_vs_theoretical.png",
            "phase3_quantity_batch_distribution.png",
            "phase3_size_distribution_by_sku.png",
            "phase3_stream_reproducibility_and_sensitivity.png"
        ],
        "phase4": [
            "phase4_adaptive_features_radar.png",
            "phase4_delta_mi_and_tau_feasibility.png",
            "phase4_mixing_index_properties.png",
            "phase4_single_vs_split_lookahead.png",
            "phase4_top_k_benchmark.png"
        ],
        "phase5": [
            "phase5_adaptive_weights_evolution.png",
            "phase5_cross_agent_comparison.png",
            "phase5_heuristic_pilot_trajectory.png",
            "phase5_supervised_gate_distribution.png"
        ]
    }
    for phase, fig_list in expected_figures.items():
        for fig_name in fig_list:
            p = outputs_dir / "figures" / fig_name
            assert p.exists(), f"Figure {fig_name} missing for {phase}!"
            assert p.stat().st_size > 50000, f"Figure {fig_name} seems suspiciously small (<50KB)!"


def test_all_tables_exist(outputs_dir):
    """Verify that structured data tables exist for all phases."""
    expected_tables = {
        "phase1": ["data_profile.csv", "baseline_mi_by_scope.csv", "scope_justification.csv", "policy_comparison.csv", "phase1_coordinate_duplicate_audit.csv"],
        "phase2": ["location_level_mi_z34.csv", "snapshot_mi_before_after_release.csv", "phase2_capacity_summary.csv"],
        "phase3": ["event_stream_quantity_distribution.csv", "event_stream_summary.csv", "event_stream_top_skus.csv", "phase3_sensitivity_streams_comparison.csv"],
        "phase4": ["phase4_benchmark_summary.csv", "phase4_tau_feasibility_matrix.csv"],
        "phase5": ["phase5_pilot_comparison_summary.csv", "phase5_adaptive_weights_evolution.csv"]
    }
    for phase, tbl_list in expected_tables.items():
        for tbl_name in tbl_list:
            p = outputs_dir / "tables" / tbl_name
            assert p.exists(), f"Table {tbl_name} missing for {phase}!"
            df = pd.read_csv(p)
            assert len(df) > 0, f"Table {tbl_name} is empty!"


def test_all_metrics_exist(outputs_dir):
    """Verify that quantitative metric CSVs exist for all phases."""
    expected_metrics = [
        "metrics_phase1_audit.csv",
        "metrics_phase2_state.csv",
        "metrics_phase3_events.csv",
        "metrics_phase4_allocation.csv",
        "metrics_phase5_agents_summary.csv",
        "metrics_heuristic.csv",
        "metrics_supervised.csv",
        "metrics_adaptive.csv"
    ]
    for m in expected_metrics:
        p = outputs_dir / "metrics" / m
        assert p.exists(), f"Metric file {m} missing!"
        df = pd.read_csv(p)
        assert len(df) > 0, f"Metric file {m} is empty!"


def test_all_logs_exist(outputs_dir):
    """Verify that execution/audit logs exist for all phases."""
    expected_logs = [
        "phase1_data_audit_log.csv",
        "phase2_state_release_log.csv",
        "phase3_generation_audit_log.csv",
        "phase4_allocation_benchmark_log.csv",
        "actions_heuristic.csv",
        "actions_supervised.csv",
        "actions_adaptive.csv"
    ]
    for log_name in expected_logs:
        p = outputs_dir / "logs" / log_name
        assert p.exists(), f"Log file {log_name} missing!"
        df = pd.read_csv(p)
        assert len(df) > 0, f"Log file {log_name} is empty!"
