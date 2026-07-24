from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Callable

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
    except Exception:
        pass
    try:
        import kilosort

        result["kilosort_available"] = True
        result["kilosort_version"] = getattr(kilosort, "__version__", "unknown")
    except Exception:
        pass
    return result


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
    returned = run_kilosort(**kwargs)

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
