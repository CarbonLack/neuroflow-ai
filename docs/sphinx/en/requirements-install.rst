System requirements and installation
====================================

Choose the installation route according to the task you intend to run.
Browsing a project, reviewing figures, or importing processed spike times
requires substantially less hardware than sorting a long high-density
recording.

Minimum practical configuration
--------------------------------

* 64-bit Windows 10/11 for the packaged application. Users do not need Python
  or Conda.
* 16 GB RAM for short teaching data; 32 GB or more for routine multichannel
  work.
* Sufficient free storage for the original recording, standardized cache,
  sorter-native output, and exported figures.
* A supported NVIDIA GPU for Kilosort4. CPU sorters remain selectable when a
  compatible backend has passed the environment check.

Install the Windows application
-------------------------------

Download ``NeuroEphysAI-Setup-1.1.1.exe`` from GitHub **Releases** or the
competition delivery folder. The per-user installer requires no administrator
access and creates desktop and Start-menu shortcuts. Uninstalling the program
does not delete projects under ``Documents\NeuroEphysAI``.

The portable ``NeuroEphysAI-1.1.1-Windows-x64-portable.zip`` needs no
installation. Extract the complete archive and run
``NeuroEphysAI\NeuroEphysAI.exe``; the EXE does not work by itself. This
one-folder layout keeps scientific libraries inspectable and avoids unpacking
them at every launch.

Both editions run data import, QC, existing sorting import, Unit curation,
behavior, statistics, machine learning, Elephant, figures, AI controls, and
the manual locally. The CUDA-enabled PyTorch runtime required by Kilosort4 is
several GiB and is therefore managed as a separate GPU component. The Sorter
page displays the actual state and never substitutes another sorter.

The first launch performs an environment inventory. Open **Sorter manager** to
see the detected backend, version, device requirement, probe suitability, and
actual runnable state. A listed sorter is not considered runnable until its
probe succeeds.

Python package
--------------

The validated Python distribution targets 64-bit Python 3.12:

.. code-block:: powershell

   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install neuroephys_ai-1.1.1-py3-none-any.whl
   .\.venv\Scripts\neuroephys.exe info

.. code-block:: python

   from pathlib import Path
   import neuroephys as ne

   project = ne.create_simulated_project(Path("example_project"))
   qc = ne.run_raw_qc(project)

The ``desktop``, ``mountainsort``, and ``kilosort`` extras are optional. The
last two require a compatible C++ build environment or NVIDIA GPU/CUDA stack,
respectively, and cannot block installation of the core package.

After creating ``.venv``, a Windows research workstation can install and probe
all six entries in the curated product catalog in one operation:

.. code-block:: powershell

   powershell -ExecutionPolicy Bypass -File scripts\setup_all_sorters.ps1

The script installs CUDA PyTorch, Kilosort4, MountainSort5/isosplit6, and the
SpikeInterface internal sorters, then reports their actual availability. Other
SpikeInterface wrappers can require MATLAB, containers, separate licenses, or
platform tools and are not shown as runnable without a tested product adapter.

Source development installation
-------------------------------

.. code-block:: powershell

   git clone https://github.com/CarbonLack/neuroflow-ai.git
   cd neuroflow-ai
   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
   .\.venv\Scripts\python.exe app.py

Run the tests before working with your own recording:

.. code-block:: powershell

   .\.venv\Scripts\python.exe -m pytest -q

Sorter environments
-------------------

Kilosort4 uses its installed Python and CUDA stack. MountainSort5 and several
SpikeInterface sorters can run on CPU. NeuroEphys AI records the backend
selected by the user and preserves each native output directory. A failed
backend remains failed; the application does not silently substitute another
sorter.

Developers can build the portable application, Python packages, installer, and
checksums with ``scripts\build_release.ps1``. The managed full GPU build remains
available through ``scripts\build_windows.ps1``.

.. warning::

   The v1.0 support boundary is 64-bit Windows 10/11 and Python 3.12. macOS,
   Linux, and other Python versions are not part of this release's formal
   compatibility claim.
