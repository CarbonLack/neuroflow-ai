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
from neuroflow.product import PRODUCT_VERSION

release_series = ".".join(PRODUCT_VERSION.split(".")[:2])

python_runtime_dirs = [
    Path(sys.base_prefix) / "DLLs",
    Path(sys.base_prefix),
]
lite_build = os.environ.get("NEUROEPHYS_LITE_BUILD", "").strip() == "1"
# PyInstaller resolves transitive DLLs through PATH. Prefer the OpenSSL build
# shipped with this Python runtime over unrelated Conda installations.
runtime_path = os.pathsep.join(
    str(directory) for directory in python_runtime_dirs if directory.exists()
)
os.environ["PATH"] = f"{runtime_path}{os.pathsep}{os.environ.get('PATH', '')}"

datas = []
binaries = [
    (str(directory / name), ".")
    for directory in python_runtime_dirs
    for name in (
        "libssl-3-x64.dll",
        "libcrypto-3-x64.dll",
        "libssl-3.dll",
        "libcrypto-3.dll",
    )
    if (directory / name).is_file()
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
        "._test",
        ".conftest",
        ".benchmark",
        ".bench",
        "._build_utils",
        "mountainsort5.quip",
        "kilosort.gui",
    )
    return not any(part in name for part in blocked_parts)


packages = [
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
]
if not lite_build:
    packages.insert(0, "kilosort")

for package in packages:
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

datas += [
    ("docs/site", "neuroflow_docs"),
    ("assets/brand", "neuroephys_brand"),
    ("README_FIRST.md", "."),
    (f"RELEASE_NOTES_{release_series}.md", "."),
    (f"RELEASE_VALIDATION_{release_series}.md", "."),
    ("THIRD_PARTY_SOURCES.md", "."),
    ("PROJECT_RIGHTS_NOTICE_ZH.md", "."),
]

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
    excludes=(
        [
            "torch",
            "kilosort",
            "tensorflow",
            "pytest",
            "_pytest",
            "sphinx",
            "docutils",
            "twine",
            "build",
        ]
        if lite_build
        else []
    ),
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="NeuroEphysAI",
    icon="assets/brand/neuroephys-ai.ico",
    version="assets/windows_version_info.txt",
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
