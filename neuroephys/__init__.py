from __future__ import annotations

"""Public Python API for NeuroEphys AI.

Typical usage::

    from pathlib import Path
    import neuroephys as ne

    project = ne.create_simulated_project(Path("my_project"))
    qc = ne.run_raw_qc(project)

Public functions are imported only when first accessed.  This keeps
``import neuroephys`` lightweight and prevents optional sorter or GUI runtimes
from being loaded unless they are actually used.
"""

from importlib import import_module
from typing import Any

from neuroflow.product import PRODUCT_VERSION

from ._exports import PUBLIC_EXPORTS

__version__ = PRODUCT_VERSION
__all__ = ["__version__", *PUBLIC_EXPORTS]


def __getattr__(name: str) -> Any:
    target = PUBLIC_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
