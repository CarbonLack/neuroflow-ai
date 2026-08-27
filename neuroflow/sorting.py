from __future__ import annotations

import importlib.metadata
import inspect
import json
import os
import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

import numpy as np

from .models import ProjectState
from .recording_io import prepare_interleaved_binary
from .sorting_results import compare_sorting_results, register_sorting_result

SORTER_DEFINITIONS = (
    {
        "key": "kilosort4",
        "name": "Kilosort4",
        "hardware": "NVIDIA GPU recommended",
        "best_for": "High-density silicon probes / Neuropixels",
        "backend": "Native NeuroEphys AI adapter",
        "package": "kilosort",
    },
    {
        "key": "mountainsort5",
        "name": "MountainSort5",
        "hardware": "CPU",
        "best_for": "Tetrodes and low-to-medium channel-count recordings",
        "backend": "SpikeInterface",
        "package": "mountainsort5",
    },
    {
        "key": "spykingcircus2",
        "name": "SpyKING CIRCUS 2",
        "hardware": "CPU; GPU is optional",
        "best_for": "General multichannel extracellular recordings",
        "backend": "SpikeInterface internal sorter",
        "package": "spikeinterface",
    },
    {
        "key": "tridesclous2",
        "name": "Tridesclous 2",
        "hardware": "CPU",
        "best_for": "Low-to-medium channel-count recordings",
        "backend": "SpikeInterface internal sorter",
        "package": "spikeinterface",
    },
    {
        "key": "simple",
        "name": "SpikeInterface Simple",
        "hardware": "CPU",
        "best_for": "Fast teaching, preview, and pipeline checks",
        "backend": "SpikeInterface internal sorter",
        "package": "spikeinterface",
    },
    {
        "key": "lupin",
        "name": "Lupin",
        "hardware": "CPU",
        "best_for": "SpikeInterface-native experimental comparison",
        "backend": "SpikeInterface internal sorter",
        "package": "spikeinterface",
    },
)

INSTALL_GUIDANCE = {
    "mountainsort5": (
        "MountainSort5 requires isosplit6. The NeuroEphys AI Windows release bundles the "
        "compiled dependency; source installations on Python 3.12 require Microsoft "
        "C++ Build Tools."
    ),
}


def _package_version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def kilosort_environment() -> dict:
    result = {
        "kilosort_available": False,
        "kilosort_version": None,
        "torch_available": False,
        "torch_version": None,
        "cuda_available": False,
        "device_name": "CPU",
        "gpu_memory_gb": 0.0,
    }
    try:
        import torch

        result["torch_available"] = True
        result["torch_version"] = torch.__version__
        result["cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            result["device_name"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            result["gpu_memory_gb"] = props.total_memory / 1024**3
    except Exception as exc:  # noqa: BLE001 - environment probes must never crash the UI
        result["torch_error"] = f"{type(exc).__name__}: {exc}"
    try:
        import kilosort

        result["kilosort_available"] = True
        result["kilosort_version"] = getattr(kilosort, "__version__", "unknown")
    except Exception as exc:  # noqa: BLE001 - optional backend
        result["kilosort_error"] = f"{type(exc).__name__}: {exc}"
    return result


def _spikeinterface_sorter_status(sorter_name: str) -> tuple[bool, str | None]:
    """Probe one allow-listed sorter without enumerating unrelated backends.

    SpikeInterface ``installed_sorters()`` checks every registered external sorter.
    On Windows, one of those checks can emit a non-UTF-8 subprocess stream.  A
    failure in HDSort or a MATLAB wrapper must not prevent NeuroEphys AI from opening.
    """
    try:
        import spikeinterface.sorters as ss

        sorter_class = ss.sorter_dict.get(sorter_name)
        if sorter_class is None:
            return False, "Sorter is not registered by this SpikeInterface version"
        return bool(sorter_class.is_installed()), None
    except Exception as exc:  # noqa: BLE001 - isolate every optional backend probe
        return False, f"{type(exc).__name__}: {exc}"


@lru_cache(maxsize=1)
def sorter_catalog() -> list[dict]:
    """Return the status of NeuroEphys AI's explicitly supported sorters."""
    ks_env = kilosort_environment()
    catalog = []
    for definition in SORTER_DEFINITIONS:
        item = dict(definition)
        if item["key"] == "kilosort4":
            installed = bool(ks_env["kilosort_available"])
            error = ks_env.get("kilosort_error")
            version = ks_env.get("kilosort_version")
        else:
            installed, error = _spikeinterface_sorter_status(item["key"])
            version = _package_version(item["package"])
            if not installed and not error:
                error = INSTALL_GUIDANCE.get(
                    item["key"],
                    "The optional sorter package is not installed.",
                )
        item.update(
            {
                "installed": installed,
                "version": version or "not installed",
                "error": error,
            }
        )
        catalog.append(item)
    return catalog


def refresh_sorter_catalog() -> list[dict]:
    sorter_catalog.cache_clear()
    return sorter_catalog()


def _channel_locations(
    channel_count: int,
    stored_locations: list | np.ndarray | None = None,
) -> np.ndarray:
    if stored_locations is not None:
        locations = np.asarray(stored_locations, dtype=float)
        if locations.shape == (channel_count, 2) and np.all(np.isfinite(locations)):
            return locations
    rows = np.arange(channel_count)
    return np.column_stack(((rows % 2) * 20.0, (rows // 2) * 20.0))


def _attach_probe(recording, state: ProjectState):
    channel_count = recording.get_num_channels()
    probe_metadata = state.metadata.get("probe", {})
    stored_locations = state.metadata.get("contact_positions_um")
    independent_contacts = (
        stored_locations is None
        and probe_metadata.get("geometry_mode") == "independent_contacts"
    )
    if independent_contacts:
        locations = np.column_stack(
            (np.arange(channel_count, dtype=float) * 1_000.0, np.zeros(channel_count))
        )
        shank_ids = np.arange(channel_count).astype(str)
    else:
        locations = _channel_locations(channel_count, stored_locations)
        stored_shanks = state.metadata.get("contact_shank_ids")
        shank_ids = (
            np.asarray(stored_shanks).astype(str)
            if stored_shanks is not None and len(stored_shanks) == channel_count
            else np.zeros(channel_count, dtype=str)
        )
    try:
        from probeinterface import Probe

        probe = Probe(ndim=2, si_units="um")
        probe.set_contacts(
            positions=locations,
            shapes="circle",
            shape_params={"radius": 6},
            shank_ids=shank_ids,
        )
        probe.set_device_channel_indices(np.arange(channel_count))
        return recording.set_probe(probe, in_place=False)
    except Exception:  # noqa: BLE001 - location fallback supports older versions
        recording.set_channel_locations(locations)
        if independent_contacts and hasattr(recording, "set_channel_groups"):
            recording.set_channel_groups(np.arange(channel_count))
        return recording


def run_sorter(
    state: ProjectState,
    sorter_name: str,
    results_dir: Path,
    progress: Callable[[str], None] | None = None,
    settings: dict | None = None,
    *,
    activate: bool = True,
    update_comparison: bool = True,
) -> dict[int, np.ndarray]:
    if sorter_name == "kilosort4":
        return run_kilosort4(state, results_dir, progress, settings)
    available = {item["key"]: item for item in refresh_sorter_catalog()}
    item = available.get(sorter_name)
    if item is None:
        raise ValueError(f"Unknown sorter: {sorter_name}")
    if not item["installed"]:
        detail = f" ({item['error']})" if item.get("error") else ""
        raise RuntimeError(
            f"{item['name']} is integrated but is not available in this environment"
            f"{detail}. Open the sorter manager to inspect installation status."
        )
    if not state.ready:
        raise RuntimeError("This sorter requires a raw voltage recording")

    import spikeinterface as si
    import spikeinterface.sorters as ss

    if state.metadata.get("recording_adapter", {}).get("type") == "spikeinterface":
        sorting_input = prepare_interleaved_binary(
            state,
            state.root / "cache" / "sorting_input_selected_channels.bin",
            progress,
        )
    else:
        sorting_input = state.recording_path
    recording = si.read_binary(
        file_paths=[sorting_input],
        sampling_frequency=state.sampling_rate,
        num_channels=state.channel_count,
        dtype=state.dtype,
        gain_to_uV=state.scale_uv_per_bit,
    )
    recording = _attach_probe(recording, state)
    if progress:
        progress(f"{item['name']} is running through SpikeInterface")
    sorter_settings = dict(settings or {})
    default_settings = ss.get_default_sorter_params(sorter_name)
    automatic_adjustments: list[str] = []
    source_preprocessed = bool(
        state.metadata.get("acquisition_preprocessing", {}).get(
            "ap_preprocessed"
        )
    )
    if source_preprocessed and sorter_name == "mountainsort5":
        if "filter" not in sorter_settings:
            sorter_settings["filter"] = False
            automatic_adjustments.append(
                "Disabled MountainSort5 filtering because the acquisition "
                "metadata reports an online AP filter."
            )
    if source_preprocessed and sorter_name == "spykingcircus2":
        if "apply_preprocessing" not in sorter_settings:
            sorter_settings["apply_preprocessing"] = False
            automatic_adjustments.append(
                "Disabled SpyKING CIRCUS 2 filtering/reference preprocessing "
                "because equivalent processing was applied during acquisition."
            )
    if source_preprocessed and sorter_name == "tridesclous2":
        if "apply_preprocessing" not in sorter_settings:
            sorter_settings["apply_preprocessing"] = False
            automatic_adjustments.append(
                "Disabled Tridesclous 2 preprocessing because the acquisition "
                "metadata reports an online AP filter and reference."
            )
    if sorter_name == "spykingcircus2" and os.name == "nt":
        if "cache_preprocessing" not in sorter_settings:
            sorter_settings["cache_preprocessing"] = {
                "mode": "no-cache",
                "memory_limit": 0.5,
            }
            automatic_adjustments.append(
                "Disabled whole-recording shared-memory caching on Windows."
            )
    if progress:
        for adjustment in automatic_adjustments:
            progress(adjustment)
    if "freq_max" in default_settings:
        nyquist = state.sampling_rate / 2
        default_max = float(default_settings["freq_max"])
        if default_max >= nyquist:
            adjusted_max = max(
                float(default_settings.get("freq_min", 300)) + 100,
                nyquist * 0.9,
            )
            sorter_settings["freq_max"] = adjusted_max
            if progress:
                progress(
                    f"{item['name']} freq_max adjusted to {adjusted_max:.0f} Hz "
                    f"for a {state.sampling_rate:.0f} Hz recording"
                )
    filtering = default_settings.get("filtering")
    if isinstance(filtering, dict) and float(filtering.get("freq_max", 0)) >= (
        state.sampling_rate / 2
    ):
        adjusted_filtering = dict(filtering)
        adjusted_filtering["freq_max"] = state.sampling_rate * 0.45
        sorter_settings["filtering"] = adjusted_filtering
        if progress:
            progress(
                f"{item['name']} filtering.freq_max adjusted to "
                f"{adjusted_filtering['freq_max']:.0f} Hz"
            )
    sorting = ss.run_sorter(
        sorter_name=sorter_name,
        recording=recording,
        folder=results_dir,
        remove_existing_folder=True,
        verbose=True,
        **sorter_settings,
    )
    sorted_spikes = {
        int(unit): sorting.get_unit_spike_train(unit).astype(float)
        / state.sampling_rate
        for unit in sorting.unit_ids
    }
    provenance = {
        "sorter": item["name"],
        "sorter_key": sorter_name,
        "version": item["version"],
        "backend": item["backend"],
        "settings": sorter_settings,
        "result_directory": str(results_dir),
        "sorting_input": str(sorting_input),
        "linked_source": str(state.source_path) if state.source_path else None,
        "automatic_adjustments": automatic_adjustments,
    }
    register_sorting_result(
        state,
        sorter_name,
        sorted_spikes,
        provenance,
        activate=activate,
    )
    if update_comparison:
        compare_sorting_results(state)
    state.log(f"{item['name']} completed: {len(sorted_spikes)} units")
    return sorted_spikes


def load_spikeinterface_result(
    state: ProjectState,
    sorter_name: str,
    results_dir: Path,
    *,
    activate: bool = True,
    update_comparison: bool = True,
) -> dict[int, np.ndarray]:
    """Register an existing SpikeInterface sorter folder without rerunning it."""
    import spikeinterface.sorters as ss

    results_dir = Path(results_dir)
    sorting = ss.read_sorter_folder(
        results_dir,
        register_recording=False,
        sorting_info=True,
    )
    sorted_spikes = {
        int(unit): sorting.get_unit_spike_train(unit).astype(float)
        / state.sampling_rate
        for unit in sorting.unit_ids
    }
    log_path = results_dir / "spikeinterface_log.json"
    log_data: dict = {}
    if log_path.is_file():
        try:
            log_data = json.loads(log_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            log_data = {}
    item = next(
        (
            definition
            for definition in SORTER_DEFINITIONS
            if definition["key"] == sorter_name
        ),
        {
            "name": sorter_name,
            "backend": "SpikeInterface",
            "package": "spikeinterface",
        },
    )
    provenance = {
        "sorter": item["name"],
        "sorter_key": sorter_name,
        "version": _package_version(item["package"]) or "unknown",
        "backend": item["backend"],
        "settings": log_data.get("sorter_params", {}),
        "result_directory": str(results_dir),
        "recovered_from_existing_output": True,
        "spikeinterface_log": str(log_path) if log_path.is_file() else None,
    }
    register_sorting_result(
        state,
        sorter_name,
        sorted_spikes,
        provenance,
        activate=activate,
    )
    if update_comparison:
        compare_sorting_results(state)
    state.log(
        f"{item['name']} restored from standard output: "
        f"{len(sorted_spikes)} units"
    )
    return sorted_spikes


def _probe(state: ProjectState) -> dict[str, np.ndarray | int]:
    channel_count = state.channel_count
    stored_locations = state.metadata.get("contact_positions_um")
    probe_metadata = state.metadata.get("probe", {})
    independent_contacts = (
        stored_locations is None
        and probe_metadata.get("geometry_mode") == "independent_contacts"
    )
    if independent_contacts:
        locations = np.column_stack(
            (np.arange(channel_count, dtype=float) * 200.0, np.zeros(channel_count))
        )
        kcoords = np.arange(channel_count, dtype=np.float32)
    else:
        locations = _channel_locations(channel_count, stored_locations)
        stored_shanks = state.metadata.get("contact_shank_ids")
        kcoords = (
            np.asarray(stored_shanks, dtype=np.float32)
            if stored_shanks is not None and len(stored_shanks) == channel_count
            else np.zeros(channel_count, dtype=np.float32)
        )
    return {
        "chanMap": np.arange(channel_count, dtype=np.int32),
        "xc": locations[:, 0].astype(np.float32),
        "yc": locations[:, 1].astype(np.float32),
        "kcoords": kcoords,
        "n_chan": channel_count,
    }


def _probe_provenance(state: ProjectState) -> dict:
    probe_metadata = state.metadata.get("probe", {})
    stored_locations = state.metadata.get("contact_positions_um")
    if stored_locations is not None:
        geometry_source = "project contact_positions_um"
    elif probe_metadata.get("geometry_mode") == "independent_contacts":
        geometry_source = "project-declared independent contacts"
    else:
        geometry_source = "NeuroEphys AI fallback layout"
    return {
        "probe_geometry_source": geometry_source,
        "probe_geometry_mode": probe_metadata.get("geometry_mode", "unspecified"),
        "brain_region": probe_metadata.get("brain_region"),
        "reference_configuration": probe_metadata.get("reference_configuration"),
    }


def kilosort_runtime_summary(results_dir: Path) -> dict:
    """Parse Kilosort's own timing report while preserving the original log."""
    log_path = Path(results_dir) / "kilosort4.log"
    if not log_path.exists():
        return {}
    text = log_path.read_text(encoding="utf-8", errors="replace")
    total_match = re.search(r"Total runtime:?\s+([0-9.]+)s", text)
    step_names = {
        "preprocessing": "preprocessing",
        "drift corr": "drift_correction",
        "spike det. (univ)": "universal_spike_detection",
        "cluster (temp)": "template_clustering",
        "spike det. (learn)": "learned_spike_detection",
        "cluster (final)": "final_clustering",
        "cluster merge": "cluster_merge",
        "postprocessing": "postprocessing",
    }
    steps = {}
    for source_name, key in step_names.items():
        match = re.search(
            rf"{re.escape(source_name)}:\s+([0-9.]+)s",
            text,
        )
        if match:
            steps[key] = float(match.group(1))
    return {
        "log_file": str(log_path),
        "total_runtime_seconds": (
            float(total_match.group(1)) if total_match else None
        ),
        "steps_seconds": steps,
    }


def load_kilosort4_result(
    state: ProjectState,
    results_dir: Path,
    *,
    recovered: bool = True,
    sorter_key: str = "kilosort4",
) -> dict[int, np.ndarray]:
    """Register an existing Kilosort4 output without rerunning the sorter."""
    results_dir = Path(results_dir)
    spike_times_candidates = list(results_dir.rglob("spike_times.npy"))
    if not spike_times_candidates:
        raise FileNotFoundError(
            f"No spike_times.npy was found under {results_dir}"
        )
    spike_times_path = spike_times_candidates[0]
    spike_clusters_path = spike_times_path.with_name("spike_clusters.npy")
    if not spike_clusters_path.exists():
        raise FileNotFoundError(
            f"Missing Kilosort cluster assignment: {spike_clusters_path}"
        )

    sample_indices = np.asarray(
        np.load(spike_times_path, mmap_mode="r")
    ).reshape(-1)
    cluster_ids = np.asarray(
        np.load(spike_clusters_path, mmap_mode="r")
    ).reshape(-1)
    if len(sample_indices) != len(cluster_ids):
        raise ValueError(
            "Kilosort spike_times.npy and spike_clusters.npy have different lengths"
        )
    sorted_spikes = {
        int(unit_id): sample_indices[cluster_ids == unit_id].astype(np.float64)
        / state.sampling_rate
        for unit_id in np.unique(cluster_ids)
    }

    summary_path = results_dir / "neuroflow_sorting_summary.json"
    summary = {}
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    environment = summary.get("environment", {})
    settings = summary.get("settings", {})
    provenance = {
        "sorter": "Kilosort4",
        "sorter_key": sorter_key,
        "backend": (
            "Existing Kilosort4 / Phy-compatible output"
            if recovered
            else "Native NeuroEphys AI adapter"
        ),
        "version": environment.get("kilosort_version", "unknown"),
        "device": environment.get("device_name", "unknown"),
        "settings": settings,
        "result_directory": str(results_dir),
        "diagnostic_files": sorted(
            path.name for path in results_dir.iterdir() if path.is_file()
        ),
        "recovered_from_existing_output": bool(recovered),
        "time_source": "Kilosort sample indices divided by recording sampling rate",
        "runtime_timing": kilosort_runtime_summary(results_dir),
        **_probe_provenance(state),
    }
    register_sorting_result(state, sorter_key, sorted_spikes, provenance)
    compare_sorting_results(state)
    state.log(
        f"Kilosort4 result loaded: {len(sorted_spikes)} units, "
        f"{sum(len(value) for value in sorted_spikes.values())} spikes"
    )
    return sorted_spikes


def run_kilosort4(
    state: ProjectState,
    results_dir: Path,
    progress: Callable[[str], None] | None = None,
    user_settings: dict | None = None,
    *,
    sorter_key: str = "kilosort4",
) -> dict[int, np.ndarray]:
    if not state.ready:
        raise RuntimeError("Raw recording is not available")
    env = kilosort_environment()
    if not env["kilosort_available"]:
        raise RuntimeError("Kilosort4 is not installed in this analysis environment")

    import torch
    from kilosort import run_kilosort

    results_dir.mkdir(parents=True, exist_ok=True)
    if progress:
        progress(
            f"Kilosort4 {env['kilosort_version']} on {env['device_name']} is running"
        )

    settings = {
        "n_chan_bin": state.channel_count,
        "fs": state.sampling_rate,
        "batch_size": 60_000,
        "nblocks": 0,
        "Th_universal": 9,
        "Th_learned": 8,
        "artifact_threshold": 12_000,
    }
    requested = dict(user_settings or {})
    save_extra_vars = bool(requested.pop("save_extra_vars", True))
    settings.update(requested)
    settings["n_chan_bin"] = state.channel_count
    settings["fs"] = state.sampling_rate
    sorting_input = prepare_interleaved_binary(
        state,
        state.root / "cache" / "sorting_input_selected_channels.bin",
        progress,
    )
    source_preprocessed = bool(
        state.metadata.get("acquisition_preprocessing", {}).get("ap_preprocessed")
    )
    kwargs = {
        "settings": settings,
        "probe": _probe(state),
        "filename": sorting_input,
        "results_dir": results_dir,
        "data_dtype": state.dtype,
        "do_CAR": not source_preprocessed,
        "invert_sign": False,
        "device": torch.device("cuda" if torch.cuda.is_available() else "cpu"),
        "clear_cache": True,
        "save_extra_vars": save_extra_vars,
        "verbose_log": True,
    }
    signature = inspect.signature(run_kilosort)
    kwargs = {
        key: value for key, value in kwargs.items() if key in signature.parameters
    }
    outputs = run_kilosort(**kwargs)

    spike_times_path = results_dir / "spike_times.npy"
    spike_clusters_path = results_dir / "spike_clusters.npy"
    if not spike_times_path.exists():
        candidates = list(results_dir.rglob("spike_times.npy"))
        if not candidates:
            raise RuntimeError(
                "Kilosort finished, but spike_times.npy was not generated"
            )
        spike_times_path = candidates[0]
        spike_clusters_path = spike_times_path.with_name("spike_clusters.npy")
    sample_indices = np.load(spike_times_path).reshape(-1)
    cluster_ids = np.load(spike_clusters_path).reshape(-1)
    sorted_spikes = {
        int(unit_id): sample_indices[cluster_ids == unit_id].astype(np.float64)
        / state.sampling_rate
        for unit_id in np.unique(cluster_ids)
    }
    provenance = {
        "sorter": "Kilosort4",
        "sorter_key": sorter_key,
        "backend": "Native NeuroEphys AI adapter",
        "version": env["kilosort_version"],
        "device": env["device_name"],
        "settings": settings,
        "result_directory": str(results_dir),
        "save_extra_vars": save_extra_vars,
        "diagnostic_files": sorted(
            path.name for path in results_dir.iterdir() if path.is_file()
        ),
        "sorting_input": str(sorting_input),
        "linked_source": str(state.source_path) if state.source_path else None,
        "common_average_reference_applied_by_kilosort": not source_preprocessed,
        "runtime_timing": kilosort_runtime_summary(results_dir),
        **_probe_provenance(state),
    }
    if isinstance(outputs, tuple) and len(outputs) >= 9:
        _, st, clu, _, _, similar_templates, is_ref, contam, kept = outputs[:9]
        provenance["runtime_summary"] = {
            "detected_spikes_before_deduplication": len(st),
            "cluster_count_before_export": len(np.unique(clu)),
            "refractory_cluster_count": int(np.count_nonzero(is_ref)),
            "median_contamination": float(np.nanmedian(contam)),
            "kept_spike_fraction": float(np.mean(kept)),
            "similarity_matrix_shape": list(np.shape(similar_templates)),
        }
    register_sorting_result(state, sorter_key, sorted_spikes, provenance)
    compare_sorting_results(state)
    state.log(
        f"Kilosort4 completed: {len(sorted_spikes)} units, "
        f"{sum(len(value) for value in sorted_spikes.values())} spikes"
    )
    (results_dir / "neuroflow_sorting_summary.json").write_text(
        json.dumps(
            {
                "environment": env,
                "settings": settings,
                "unit_count": len(sorted_spikes),
                "spike_count": int(sum(len(value) for value in sorted_spikes.values())),
                "runtime_timing": kilosort_runtime_summary(results_dir),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if progress:
        progress(f"Sorting completed: {len(sorted_spikes)} units")
    return sorted_spikes
