"""Build-time Windows version resource derived from the application version."""
from .product import PRODUCT_NAME, PRODUCT_VERSION


def build_windows_version_info():
    from PyInstaller.utils.win32.versioninfo import (
        VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable,
        StringStruct, VarFileInfo, VarStruct,
    )
    version = tuple(int(part) for part in PRODUCT_VERSION.split(".")) + (0,)
    fields = {
        "CompanyName": "NeuroEphys AI team",
        "FileDescription": "NeuroEphys AI electrophysiology workbench",
        "FileVersion": PRODUCT_VERSION,
        "InternalName": "NeuroEphysAI",
        "LegalCopyright": "Copyright 2026 NeuroEphys AI team",
        "OriginalFilename": "NeuroEphysAI.exe",
        "ProductName": PRODUCT_NAME,
        "ProductVersion": PRODUCT_VERSION,
    }
    return VSVersionInfo(ffi=FixedFileInfo(filevers=version, prodvers=version,
        mask=0x3F, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
        kids=[StringFileInfo([StringTable("080404B0", [StringStruct(k, v) for k, v in fields.items()])]),
              VarFileInfo([VarStruct("Translation", [2052, 1200])])])
