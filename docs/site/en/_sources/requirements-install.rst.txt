System requirements and installation
====================================

Choose the installation route according to the task you intend to run.
Browsing a project, reviewing figures, or importing processed spike times
requires substantially less hardware than sorting a long high-density
recording.

Minimum practical configuration
--------------------------------

* Windows 10/11 for the packaged development preview.
* 16 GB RAM for short teaching data; 32 GB or more for routine multichannel
  work.
* Sufficient free storage for the original recording, standardized cache,
  sorter-native output, and exported figures.
* A supported NVIDIA GPU for Kilosort4. CPU sorters remain selectable when a
  compatible backend has passed the environment check.

Development preview download
----------------------------

Download the latest prerelease from the GitHub **Releases** page, extract the
archive to a writable local folder, and run ``NeuroEphysAI.exe``. The one-folder
layout keeps scientific libraries inspectable and avoids unpacking them at each
launch.

The public archive is the portable core preview. Its data import, QC, existing
sorting import, Unit curation, behavior, statistics, machine learning,
Elephant, figures, AI controls, and manual run locally. The CUDA-enabled
PyTorch runtime required by Kilosort4 is several GiB, so it is provided by the
repository's full analysis environment rather than duplicated in the core
archive. The Sorter page displays the actual state and never substitutes
another sorter.

The first launch performs an environment inventory. Open **Sorter manager** to
see the detected backend, version, device requirement, probe suitability, and
actual runnable state. A listed sorter is not considered runnable until its
probe succeeds.

Developer installation
----------------------

.. code-block:: powershell

   git clone https://github.com/CarbonLack/neuroflow-ai.git
   cd neuroflow-ai
   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
   .\.venv312\Scripts\python.exe app.py

Run the tests before working with your own recording:

.. code-block:: powershell

   .\.venv312\Scripts\python.exe -m pytest -q

Sorter environments
-------------------

Kilosort4 uses its installed Python and CUDA stack. MountainSort5 and several
SpikeInterface sorters can run on CPU. NeuroEphys AI records the backend
selected by the user and preserves each native output directory. A failed
backend remains failed; the application does not silently substitute another
sorter.

Developers can create the full local GPU build with
``scripts\build_windows.ps1`` or the smaller downloadable core preview with
``scripts\build_windows_lite.ps1``.

.. warning::

   The packaged preview has been exercised on the development workstation. It
   has not yet completed a full compatibility matrix across clean Windows,
   macOS, and Linux machines.
