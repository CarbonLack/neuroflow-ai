from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from pathlib import Path

import numpy as np

from .models import ProjectState


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
    except (ImportError, RuntimeError):
        result["torch_error"] = "PyTorch/CUDA unavailable"
    try:
        import kilosort

        result["kilosort_available"] = True
        result["kilosort_version"] = getattr(kilosort, "__version__", "unknown")
    except ImportError:
        result["kilosort_error"] = "Kilosort4 unavailable"
    return result


def sorter_catalog() -> list[dict]:
    """Return executable capability, not a marketing-only sorter list."""
    installed: set[str] = set()
    try:
        import spikeinterface.sorters as ss

        installed = set(ss.installed_sorters())
    except (ImportError, RuntimeError):
        installed = set()
    ks_env = kilosort_environment()
    definitions = [
        {
            "key": "kilosort4",
            "name": "Kilosort4",
            "hardware": "NVIDIA GPU recommended",
            "best_for": "高密度 silicon probe / Neuropixels",
            "installed": bool(ks_env["kilosort_available"]),
            "backend": "native NeuroFlow adapter",
        },
        {
            "key": "mountainsort5",
            "name": "MountainSort5",
            "hardware": "CPU",
            "best_for": "tetrode 与中等通道记录",
            "installed": "mountainsort5" in installed,
            "backend": "SpikeInterface",
        },
        {
            "key": "spykingcircus2",
            "name": "SpyKING CIRCUS 2",
            "hardware": "CPU / GPU depending on setup",
            "best_for": "通用多通道记录",
            "installed": "spykingcircus2" in installed,
            "backend": "SpikeInterface",
        },
        {
            "key": "tridesclous2",
            "name": "Tridesclous 2",
            "hardware": "CPU",
            "best_for": "低至中等通道记录",
            "installed": "tridesclous2" in installed,
            "backend": "SpikeInterface",
        },
    ]
    return definitions


def run_sorter(
    state: ProjectState,
    sorter_name: str,
    results_dir: Path,
    progress: Callable[[str], None] | None = None,
) -> dict[int, np.ndarray]:
    if sorter_name == "kilosort4":
        return run_kilosort4(state, results_dir, progress)
    available = {item["key"]: item for item in sorter_catalog()}
    item = available.get(sorter_name)
    if item is None:
        raise ValueError(f"未知 sorter：{sorter_name}")
    if not item["installed"]:
        raise RuntimeError(
            f"{item['name']} 适配器已经注册，但依赖尚未安装；"
            "NeuroFlow 不会把未验证的 sorter 标记为可运行。"
        )
    if not state.ready:
        raise RuntimeError("该 sorter 需要原始电压记录")
    import spikeinterface as si
    import spikeinterface.sorters as ss

    recording = si.read_binary(
        file_paths=[state.recording_path],
        sampling_frequency=state.sampling_rate,
        num_channels=state.channel_count,
        dtype=state.dtype,
    )
    if progress:
        progress(f"{item['name']} 通过 SpikeInterface 开始运行")
    sorting = ss.run_sorter(
        sorter_name,
        recording,
        folder=results_dir,
        remove_existing_folder=True,
        verbose=True,
    )
    sorted_spikes = {
        int(unit): sorting.get_unit_spike_train(unit).astype(float) / state.sampling_rate
        for unit in sorting.unit_ids
    }
    state.sorted_spikes = sorted_spikes
    state.log(f"{item['name']} 完成：{len(sorted_spikes)} 个 unit")
    return sorted_spikes


def _probe(channel_count: int) -> dict[str, np.ndarray | int]:
    rows = np.arange(channel_count)
    return {
        "chanMap": np.arange(channel_count, dtype=np.int32),
        "xc": ((rows % 2) * 20).astype(np.float32),
        "yc": ((rows // 2) * 20).astype(np.float32),
        "kcoords": np.zeros(channel_count, dtype=np.float32),
        "n_chan": channel_count,
    }


def run_kilosort4(
    state: ProjectState,
    results_dir: Path,
    progress: Callable[[str], None] | None = None,
) -> dict[int, np.ndarray]:
    if not state.ready:
        raise RuntimeError("尚未准备原始记录")
    env = kilosort_environment()
    if not env["kilosort_available"]:
        raise RuntimeError("当前分析环境尚未安装Kilosort4")

    import torch
    from kilosort import run_kilosort

    results_dir.mkdir(parents=True, exist_ok=True)
    if progress:
        progress(
            f"Kilosort4 {env['kilosort_version']}，设备：{env['device_name']}，开始sorting"
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
        "data_dtype": "int16",
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
            raise RuntimeError("Kilosort运行结束，但未找到spike_times.npy")
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
    state.log(
        f"Kilosort4完成：检出{len(sorted_spikes)}个Unit，"
        f"{sum(len(v) for v in sorted_spikes.values())}个spike"
    )
    (results_dir / "neuroflow_sorting_summary.json").write_text(
        json.dumps(
            {
                "environment": env,
                "settings": settings,
                "unit_count": len(sorted_spikes),
                "spike_count": int(sum(len(v) for v in sorted_spikes.values())),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if progress:
        progress(f"sorting完成：{len(sorted_spikes)}个Unit")
    return sorted_spikes
