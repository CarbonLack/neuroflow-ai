from __future__ import annotations

import shutil
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .data_import import import_ibl_alf, import_nwb_units
from .ibl import download_bwm_example
from .models import ProjectState
from .project import MANIFEST_NAME, load_project

IBL_EID = "4ecb5d24-f5cc-402c-be28-9d0f7cb14b3a"
IBL_PID = "da8dfec1-d265-44e8-84ce-6ae9c109b8bd"
IBL_PROBE = "probe00"

BUZSAKI_DANDISET = "000552"
BUZSAKI_VERSION = "0.230630.2304"
BUZSAKI_ASSET_ID = "f36a3ffe-1aa2-4019-a8fc-07b03bb2b38e"
BUZSAKI_FILENAME = "sub-e14-2m3_ses-e14-2m3-201121_behavior+ecephys.nwb"
BUZSAKI_DOWNLOAD_URL = (
    "https://api.dandiarchive.org/api/dandisets/"
    f"{BUZSAKI_DANDISET}/versions/{BUZSAKI_VERSION}/assets/"
    f"{BUZSAKI_ASSET_ID}/download/"
)


@dataclass(frozen=True)
class PublicExample:
    key: str
    name_zh: str
    name_en: str
    source_zh: str
    source_en: str
    contents_zh: str
    contents_en: str
    identifier: str


PUBLIC_EXAMPLES = (
    PublicExample(
        key="ibl_bwm",
        name_zh="IBL Brain-Wide Map · Neuropixels",
        name_en="IBL Brain-Wide Map · Neuropixels",
        source_zh="官方 ONE/ALF 处理后会话",
        source_en="Official processed ONE/ALF session",
        contents_zh="775 Units、20,096,205 spikes、529 trials",
        contents_en="775 units, 20,096,205 spikes, 529 trials",
        identifier=f"EID {IBL_EID} · PID {IBL_PID}",
    ),
    PublicExample(
        key="buzsaki_000552",
        name_zh="Buzsáki Lab · DANDI 000552",
        name_en="Buzsáki Lab · DANDI 000552",
        source_zh="固定版本 NWB 公开档案",
        source_en="Versioned public NWB archive",
        contents_zh="56 Units、奖励事件、睡眠状态与 ripple 区间",
        contents_en="56 units, reward events, sleep states, and ripple intervals",
        identifier=(
            f"DANDI {BUZSAKI_DANDISET}/{BUZSAKI_VERSION} · "
            f"asset {BUZSAKI_ASSET_ID}"
        ),
    ),
)


def public_validation_root(workspace: Path) -> Path:
    return workspace / "PublicValidation"


def _find_ibl_alf(workspace: Path) -> Path | None:
    root = public_validation_root(workspace) / "IBL"
    if not root.exists():
        return None
    for spikes_file in root.rglob("spikes.times.npy"):
        for parent in spikes_file.parents:
            if parent.name == "alf":
                return parent
    return None


def _buzsaki_nwb_path(workspace: Path) -> Path:
    return (
        public_validation_root(workspace)
        / "Buzsaki"
        / f"DANDI_{BUZSAKI_DANDISET}"
        / BUZSAKI_FILENAME
    )


def public_example_source(workspace: Path, key: str) -> Path | None:
    if key == "ibl_bwm":
        return _find_ibl_alf(workspace)
    if key == "buzsaki_000552":
        path = _buzsaki_nwb_path(workspace)
        return path if path.is_file() else None
    raise KeyError(key)


def public_example_project_root(workspace: Path, key: str) -> Path:
    return public_validation_root(workspace) / "VerifiedProjects" / key


def public_example_status(workspace: Path, key: str) -> dict[str, object]:
    source = public_example_source(workspace, key)
    project_root = public_example_project_root(workspace, key)
    return {
        "source": source,
        "downloaded": source is not None,
        "project_root": project_root,
        "project_ready": (project_root / MANIFEST_NAME).is_file(),
    }


def download_public_example(
    workspace: Path,
    key: str,
    progress: Callable[[str], None] | None = None,
) -> Path:
    if key == "ibl_bwm":
        return download_bwm_example(
            public_validation_root(workspace) / "IBL",
            eid=IBL_EID,
            probe=IBL_PROBE,
            progress=progress,
        )
    if key == "buzsaki_000552":
        target = _buzsaki_nwb_path(workspace)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file() and target.stat().st_size > 40_000_000:
            return target
        partial = target.with_suffix(".nwb.partial")
        if progress:
            progress(
                f"Downloading DANDI {BUZSAKI_DANDISET}/{BUZSAKI_VERSION}"
            )
        request = urllib.request.Request(
            BUZSAKI_DOWNLOAD_URL,
            headers={"User-Agent": "NeuroEphys AI public-data validator"},
        )
        with (
            urllib.request.urlopen(request) as response,
            partial.open("wb") as output,
        ):
            shutil.copyfileobj(response, output, length=1024 * 1024)
        partial.replace(target)
        return target
    raise KeyError(key)


def open_or_create_public_example(
    workspace: Path,
    key: str,
) -> ProjectState:
    project_root = public_example_project_root(workspace, key)
    manifest = project_root / MANIFEST_NAME
    if manifest.is_file():
        return load_project(manifest)
    source = public_example_source(workspace, key)
    if source is None:
        raise FileNotFoundError(
            "The fixed public source is not downloaded in the NeuroEphys AI library."
        )
    if key == "ibl_bwm":
        state = import_ibl_alf(project_root, source)
        state.name = "IBL BWM Neuropixels validation"
        state.metadata.update(
            {
                "eid": IBL_EID,
                "pid": IBL_PID,
                "public_example_key": key,
            }
        )
    elif key == "buzsaki_000552":
        state = import_nwb_units(project_root, source)
        state.name = "Buzsáki DANDI 000552 validation"
        state.metadata.update(
            {
                "dandiset": BUZSAKI_DANDISET,
                "dandi_version": BUZSAKI_VERSION,
                "dandi_asset_id": BUZSAKI_ASSET_ID,
                "public_example_key": key,
            }
        )
    else:
        raise KeyError(key)
    from .project import save_project

    save_project(state)
    return state
