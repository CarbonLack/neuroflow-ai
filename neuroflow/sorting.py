from __future__ import annotations

import importlib.metadata
import inspect
import json
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

import numpy as np

from .models import ProjectState

SORTER_DEFINITIONS = (
    {
        "key": "kilosort4",
        "name": "Kilosort4",
        "hardware": "NVIDIA GPU recommended",
        "best_for": "High-density silicon probes / Neuropixels",
        "backend": "Native NeuroFlow adapter",
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
    failure in HDSort or a MATLAB wrapper must not prevent NeuroFlow from opening.
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
    """Return the status of NeuroFlow's explicitly supported sorters."""
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


def _channel_locations(channel_count: int) -> np.ndarray:
    rows = np.arange(channel_count)
    return np.column_stack(((rows % 2) * 20.0, (rows // 2) * 20.0))


def _attach_probe(recording):
    locations = _channel_locations(recording.get_num_channels())
    try:
        from probeinterface import Probe

        probe = Probe(ndim=2, si_units="um")
        probe.set_contacts(
            positions=locations,
            shapes="circle",
            shape_params={"radius": 6},
        )
        probe.set_device_channel_indices(np.arange(recording.get_num_channels()))
        return recording.set_probe(probe, in_place=False)
    except Exception:  # noqa: BLE001 - location fallback supports older versions
        recording.set_channel_locations(locations)
        return recording


def run_sorter(
    state: ProjectState,
    sorter_name: str,
    results_dir: Path,
    progress: Callable[[str], None] | None = None,
) -> dict[int, np.ndarray]:
    if sorter_name == "kilosort4":
        return run_kilosort4(state, results_dir, progress)
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

    recording = si.read_binary(
        file_paths=[state.recording_path],
        sampling_frequency=state.sampling_rate,
        num_channels=state.channel_count,
        dtype=state.dtype,
        gain_to_uV=state.scale_uv_per_bit,
    )
    recording = _attach_probe(recording)
    if progress:
        progress(f"{item['name']} is running through SpikeInterface")
    sorting = ss.run_sorter(
        sorter_name=sorter_name,
        recording=recording,
        folder=results_dir,
        remove_existing_folder=True,
        verbose=True,
    )
    sorted_spikes = {
        int(unit): sorting.get_unit_spike_train(unit).astype(float)
        / state.sampling_rate
        for unit in sorting.unit_ids
    }
    state.sorted_spikes = sorted_spikes
    state.metadata["sorting"] = {
        "sorter": item["name"],
        "sorter_key": sorter_name,
        "version": item["version"],
        "backend": item["backend"],
        "result_directory": str(results_dir),
    }
    state.log(f"{item['name']} completed: {len(sorted_spikes)} units")
    return sorted_spikes


def _probe(channel_count: int) -> dict[str, np.ndarray | int]:
    locations = _channel_locations(channel_count)
    return {
        "chanMap": np.arange(channel_count, dtype=np.int32),
        "xc": locations[:, 0].astype(np.float32),
        "yc": locations[:, 1].astype(np.float32),
        "kcoords": np.zeros(channel_count, dtype=np.float32),
        "n_chan": channel_count,
    }


def run_kilosort4(
    state: ProjectState,
    results_dir: Path,
    progress: Callable[[str], None] | None = None,
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
    kwargs = {
        "settings": settings,
        "probe": _probe(state.channel_count),
        "filename": state.recording_path,
        "results_dir": results_dir,
        "data_dtype": state.dtype,
        "do_CAR": True,
        "invert_sign": False,
        "device": torch.device("cuda" if torch.cuda.is_available() else "cpu"),
        "clear_cache": True,
    }
    signature = inspect.signature(run_kilosort)
    kwargs = {key: value for key, value in kwargs.items() if key in signature.parameters}
    run_kilosort(**kwargs)

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
    state.sorted_spikes = sorted_spikes
    state.metadata["sorting"] = {
        "sorter": "Kilosort4",
        "sorter_key": "kilosort4",
        "version": env["kilosort_version"],
        "device": env["device_name"],
        "settings": settings,
        "result_directory": str(results_dir),
    }
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
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if progress:
        progress(f"Sorting completed: {len(sorted_spikes)} units")
    return sorted_spikes
