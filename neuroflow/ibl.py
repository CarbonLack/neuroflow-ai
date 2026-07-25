from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

IBL_BWM_PAPER = "https://www.nature.com/articles/s41586-025-09235-0"
IBL_DATA_DOCS = (
    "https://docs.internationalbrainlab.org/notebooks_external/"
    "2025_data_release_brainwidemap.html"
)


FIGURE_RECIPES = [
    {
        "name": "Psychometric curve",
        "fields": ["contrastLeft", "contrastRight", "choice", "probabilityLeft"],
        "neuroflow_view": "行为分析",
        "paper_relation": "Figure 1 task behavior",
    },
    {
        "name": "Reaction time by signed contrast",
        "fields": [
            "stimOn_times",
            "firstMovement_times",
            "contrastLeft",
            "contrastRight",
        ],
        "neuroflow_view": "行为分析",
        "paper_relation": "Figure 1 reaction-time behavior",
    },
    {
        "name": "Stimulus-aligned raster and PETH",
        "fields": ["spikes.times", "spikes.clusters", "stimOn_times"],
        "neuroflow_view": "神经活动",
        "paper_relation": "Figure 4 stimulus responses",
    },
    {
        "name": "Time-resolved stimulus decoding",
        "fields": [
            "spikes.times",
            "spikes.clusters",
            "stimOn_times",
            "contrastLeft",
            "contrastRight",
        ],
        "neuroflow_view": "机器学习",
        "paper_relation": "Figure 4 decoded stimulus probability",
    },
    {
        "name": "Population PCA trajectories and distance",
        "fields": ["spikes.times", "spikes.clusters", "stimOn_times"],
        "neuroflow_view": "机器学习",
        "paper_relation": "Figure 4 population trajectories",
    },
]

PUBLIC_BUCKET = "ibl-brain-wide-map-public"
TRIALS_AGGREGATE_KEY = "aggregates/2024_Q2_IBL_et_al_BWM/trials.pqt"


def download_bwm_trials_aggregate(
    cache_dir: Path,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Download the official 24 MB aggregate table using anonymous S3."""
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config

    cache_dir.mkdir(parents=True, exist_ok=True)
    output = cache_dir / "ibl_bwm_trials_2024.pqt"
    if output.exists():
        return output
    if progress:
        progress("正在从 IBL 公共 AWS 桶下载 BWM trials aggregate（约 24 MB）")
    client = boto3.client(
        "s3",
        config=Config(
            signature_version=UNSIGNED,
            connect_timeout=10,
            read_timeout=60,
        ),
    )
    client.download_file(PUBLIC_BUCKET, TRIALS_AGGREGATE_KEY, str(output))
    if progress:
        progress(f"IBL BWM trials 已缓存：{output}")
    return output


def download_bwm_example(
    cache_dir: Path,
    eid: str | None = None,
    probe: str | None = None,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Download one processed BWM session, never the multi-hundred-GB raw AP file."""
    from one.api import ONE

    cache_dir.mkdir(parents=True, exist_ok=True)
    ONE.setup(base_url="https://openalyx.internationalbrainlab.org", silent=True)
    one = ONE(
        base_url="https://openalyx.internationalbrainlab.org",
        password="international",
        cache_dir=cache_dir,
    )
    if eid is None:
        if progress:
            progress("正在检索包含 trials 与 spikes 的 Brain-Wide Map session")
        sessions = one.search(
            project="brainwide",
            datasets=["_ibl_trials.table.pqt", "spikes.times.npy"],
            task="ephys",
        )
        if not sessions:
            raise RuntimeError("IBL ONE 未返回符合条件的公开 session")
        eid = str(sessions[0])
    if progress:
        progress(f"下载 IBL trials：{eid}")
    one.load_object(eid, "trials", collection="alf")
    datasets = one.list_datasets(eid, collection="alf/probe*")
    probe_names = sorted(
        {
            dataset.split("/")[1]
            for dataset in datasets
            if dataset.startswith("alf/probe") and len(dataset.split("/")) > 2
        }
    )
    if not probe_names:
        raise RuntimeError("该 session 未发现 probe sorting collection")
    probe = probe or probe_names[0]
    collections = sorted(
        {
            "/".join(dataset.split("/")[:-1])
            for dataset in datasets
            if f"alf/{probe}/" in dataset and dataset.endswith("spikes.times.npy")
        }
    )
    if not collections:
        collections = [f"alf/{probe}/pykilosort"]
    collection = collections[0]
    if progress:
        progress(f"下载 IBL processed spikes：{collection}")
    one.load_object(eid, "spikes", collection=collection)
    session_path = Path(one.eid2path(eid))
    if progress:
        progress(f"IBL 数据已缓存：{session_path}")
    return session_path / "alf"
