from __future__ import annotations

"""Stable public symbols exported by :mod:`neuroephys`.

The implementation continues to live in ``neuroflow`` so existing projects and
plugins remain compatible.  Keeping this table in one place makes the public
API explicit and lets the top-level package stay fast to import.
"""

PUBLIC_EXPORTS: dict[str, tuple[str, str]] = {
    # Project model and persistence
    "ProjectState": ("neuroflow.models", "ProjectState"),
    "WorkflowStep": ("neuroflow.models", "WorkflowStep"),
    "save_project": ("neuroflow.project", "save_project"),
    "load_project": ("neuroflow.project", "load_project"),
    # Data import
    "SUPPORTED_FORMATS": ("neuroflow.data_import", "SUPPORTED_FORMATS"),
    "create_simulated_project": (
        "neuroflow.data_import",
        "create_simulated_project",
    ),
    "import_binary_recording": (
        "neuroflow.data_import",
        "import_binary_recording",
    ),
    "import_device_recording": (
        "neuroflow.data_import",
        "import_device_recording",
    ),
    "import_kilosort_results": (
        "neuroflow.data_import",
        "import_kilosort_results",
    ),
    "attach_kilosort_results": (
        "neuroflow.data_import",
        "attach_kilosort_results",
    ),
    "import_ibl_alf": ("neuroflow.data_import", "import_ibl_alf"),
    "import_nwb_units": ("neuroflow.data_import", "import_nwb_units"),
    "import_ibl_trials_aggregate": (
        "neuroflow.data_import",
        "import_ibl_trials_aggregate",
    ),
    # Core analysis
    "load_recording": ("neuroflow.analysis", "load_recording"),
    "run_raw_qc": ("neuroflow.analysis", "run_raw_qc"),
    "preprocessing_preview": (
        "neuroflow.analysis",
        "preprocessing_preview",
    ),
    "compute_unit_metrics": (
        "neuroflow.analysis",
        "compute_unit_metrics",
    ),
    "match_ground_truth": ("neuroflow.analysis", "match_ground_truth"),
    "event_aligned_analysis": (
        "neuroflow.analysis",
        "event_aligned_analysis",
    ),
    "export_reproducible_bundle": (
        "neuroflow.analysis",
        "export_reproducible_bundle",
    ),
    # Synchronization and sorting
    "import_behavior_events": (
        "neuroflow.synchronization",
        "import_behavior_events",
    ),
    "synchronize_existing_events": (
        "neuroflow.synchronization",
        "synchronize_existing_events",
    ),
    "sorter_catalog": ("neuroflow.sorting", "sorter_catalog"),
    "refresh_sorter_catalog": (
        "neuroflow.sorting",
        "refresh_sorter_catalog",
    ),
    "run_sorter": ("neuroflow.sorting", "run_sorter"),
    "load_spikeinterface_result": (
        "neuroflow.sorting",
        "load_spikeinterface_result",
    ),
    "load_kilosort4_result": (
        "neuroflow.sorting",
        "load_kilosort4_result",
    ),
    "run_kilosort4": ("neuroflow.sorting", "run_kilosort4"),
    # Statistics and machine learning
    "adjust_pvalues": ("neuroflow.statistics", "adjust_pvalues"),
    "paired_effect": ("neuroflow.statistics", "paired_effect"),
    "independent_effect": ("neuroflow.statistics", "independent_effect"),
    "bootstrap_ci": ("neuroflow.statistics", "bootstrap_ci"),
    "permutation_paired": ("neuroflow.statistics", "permutation_paired"),
    "run_statistical_suite": (
        "neuroflow.statistics",
        "run_statistical_suite",
    ),
    "trial_feature_matrix": ("neuroflow.decoding", "trial_feature_matrix"),
    "run_decoding_suite": ("neuroflow.decoding", "run_decoding_suite"),
    "run_regression_suite": ("neuroflow.decoding", "run_regression_suite"),
    # Neo / Elephant toolkit
    "provider_status": ("neuroflow.ephys_toolkit", "provider_status"),
    "to_neo_spike_trains": (
        "neuroflow.ephys_toolkit",
        "to_neo_spike_trains",
    ),
    "to_neo_analog_signal": (
        "neuroflow.ephys_toolkit",
        "to_neo_analog_signal",
    ),
    "run_spike_train_suite": (
        "neuroflow.ephys_toolkit",
        "run_spike_train_suite",
    ),
    "run_lfp_suite": ("neuroflow.ephys_toolkit", "run_lfp_suite"),
    "run_spike_field_suite": (
        "neuroflow.ephys_toolkit",
        "run_spike_field_suite",
    ),
    "run_respiration_case": (
        "neuroflow.ephys_toolkit",
        "run_respiration_case",
    ),
    "run_neural_toolkit": (
        "neuroflow.ephys_toolkit",
        "run_neural_toolkit",
    ),
}
