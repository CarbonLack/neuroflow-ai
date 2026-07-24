# PyInstaller one-folder build. Scientific libraries remain inspectable and
# the application does not need to unpack them on every launch.
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

datas = []
binaries = []
hiddenimports = []
for package in (
    "kilosort",
    "spikeinterface",
    "hdbscan",
    "one",
    "sklearn",
):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

# XGBoost loads its native library at runtime, so PyInstaller cannot infer it
# from the delayed Python import in the model catalog.
binaries += collect_dynamic_libs("xgboost")

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
    name="NeuroFlow",
    console=False,
)
collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="NeuroFlow",
)
