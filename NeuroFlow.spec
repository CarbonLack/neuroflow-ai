# PyInstaller one-folder build. Scientific libraries remain inspectable and
# the application does not need to unpack them on every launch.
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
)

python_dlls = Path(sys.base_prefix) / "DLLs"
# PyInstaller resolves transitive DLLs through PATH. Prefer the OpenSSL build
# shipped with this Python runtime over unrelated Conda installations.
os.environ["PATH"] = f"{python_dlls}{os.pathsep}{os.environ.get('PATH', '')}"

datas = []
binaries = [
    (str(python_dlls / name), ".")
    for name in ("libssl-3-x64.dll", "libcrypto-3-x64.dll")
]
hiddenimports = [
    "matplotlib.backends.backend_agg",
    "matplotlib.backends.backend_pdf",
    "matplotlib.backends.backend_svg",
]


def runtime_submodule(name):
    """Keep runtime modules while excluding bundled tests and optional GUIs."""
    blocked_parts = (
        ".test",
        ".tests",
        ".conftest",
        ".benchmark",
        ".bench",
        "._build_utils",
        "mountainsort5.quip",
        "kilosort.gui",
    )
    return not any(part in name for part in blocked_parts)


for package in (
    "kilosort",
    "mountainsort5",
    "isosplit6",
    "spikeinterface",
    "neo",
    "quantities",
    "elephant",
    "hdbscan",
    "one",
    "sklearn",
    "keyring",
    "nex5file",
):
    package_datas, package_binaries, package_hidden = collect_all(
        package,
        include_py_files=False,
        filter_submodules=runtime_submodule,
        exclude_datas=[
            "**/test/**",
            "**/tests/**",
            "**/bench/**",
            "**/benchmark/**",
            "**/__pycache__/**",
        ],
    )
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

datas += [("docs/site", "neuroflow_docs")]

# XGBoost loads its native library at runtime, so PyInstaller cannot infer it
# from the delayed Python import in the model catalog.
binaries += collect_dynamic_libs("xgboost")
datas += collect_data_files("xgboost", includes=["VERSION"])

analysis = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="NeuroEphysAI",
    console=False,
)
collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="NeuroEphysAI",
)
