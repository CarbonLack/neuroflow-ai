# NeuroFlow sorter matrix

| Sorter | Execution | Typical use | Current Windows status |
|---|---|---|---|
| Kilosort4 | Native Python adapter | Neuropixels and dense silicon probes | Installed and GPU-verified |
| MountainSort5 | SpikeInterface + Python package | Tetrodes and CPU workflows | Installed and verified |
| SpyKING CIRCUS 2 | SpikeInterface internal | General multichannel recording | Installed and verified |
| Tridesclous2 | SpikeInterface internal | Low/medium channel counts | Installed and verified |
| Simple | SpikeInterface internal | Fast teaching and smoke tests | Installed and verified |
| Lupin | SpikeInterface internal | Native comparison workflow | Installed and verified |
| HerdingSpikes | SpikeInterface external | Dense MEA, localization-driven clustering | Integrated; optional backend not bundled |
| MountainSort4 | SpikeInterface external | Legacy result reproduction | Integrated; optional backend not bundled |
| WaveClus | SpikeInterface external | Independent microwires/brush or single-channel sorting | Integrated; requires MATLAB/compiled runtime |
| IronClust | SpikeInterface external | Legacy dense-probe/drift-aware comparison | Integrated; requires MATLAB/runtime |
| Kilosort 2.5 | SpikeInterface external | Reproducing old Neuropixels workflows | Integrated; requires GPU + MATLAB/runtime |

## Detection rule

NeuroFlow never calls `spikeinterface.sorters.installed_sorters()` during startup.
That function probes every registered external backend, including unrelated MATLAB
and compiled tools. NeuroFlow probes only the eleven explicit entries above and catches every
backend failure independently.

The first six are bundled runnable paths in the formal Windows analysis environment.
The other five are intentionally visible integrations so a researcher can understand
their purpose and enable them in a suitable licensed/runtime environment. A backend is
never labeled runnable merely because SpikeInterface knows its name: the application
requires an adapter, isolated environment check, provenance contract, and successful
local availability probe.

## Reproducibility

Every successful run stores sorter name, key, package version, execution backend,
result directory, Kilosort settings when applicable, and the run log in the
NeuroFlow project.

Every sorter is converted to the same `neuroflow.sorting.v1` contract:

- continuous one-based NeuroEphys AI Unit identifiers for clear downstream plots;
- sorter-native cluster identifiers retained in `source_unit_id_map` for traceability;
- monotonically increasing spike times in seconds;
- acquisition sampling rate;
- sorter name and version;
- parameters, backend, source directory, Unit count, and spike count.

Native files remain intact. The normalized view is what downstream Unit QC,
event alignment, statistics, and plotting consume.

The v0.7.0 release self-test runs SpyKING CIRCUS 2, Tridesclous2, Simple, and
Lupin independently on the same raw recording. Kilosort4 and MountainSort5 have
separate packaged self-tests because they exercise GPU and compiled-package
paths. A sorter selected before execution shows only its own input contract and
expected outputs; no completed sorter's figure is reused.

## Probe-aware examples

The example library includes distinct channel-location maps and behavior files:

- a 32-channel Neuropixels-like staggered probe with a two-choice task;
- four tetrodes (16 channels) with position, speed, and reward-zone events;
- thirty-two independent microwire/brush contacts with tone, lick, and outcome variables.

Every profile writes raw voltage, contact positions, behavior-clock events,
ephys-clock TTL pulses, a unified event table, and ground-truth spikes. The same
stored contact positions are supplied to every sorter adapter.

## Cross-sorter comparison

NeuroFlow uses SpikeInterface comparison APIs rather than comparing cluster IDs
or Unit counts:

- **one sorter plus ground truth:** accuracy, precision, recall, F1, false
  discovery rate, miss rate, and agreement matrix;
- **two sorters without ground truth:** symmetric event matching, Hungarian Unit
  assignment, agreement matrix, matched Units, and sorter-specific Units;
- **two or more sorters:** pairwise comparison graph and a consensus sorting
  supported by at least two sorters; the displayed consensus spike train uses
  SpikeInterface's intersection mode.

Agreement on a real recording is reproducibility evidence, not biological ground
truth. Precision, recall, and F1 are therefore shown only for simulation or
paired ground-truth data.

## Kilosort inspection

The workbench exposes the documented Kilosort outputs instead of showing only a
unit count: spike depth over time, amplitude stability, template waveforms,
template similarity, contamination estimates, stage timing, log tail, exported
files, and simulation ground-truth matching.

Primary references:

- https://kilosort.readthedocs.io/en/latest/gui_guide.html
- https://kilosort.readthedocs.io/en/latest/parameters.html
- https://kilosort.readthedocs.io/en/latest/export_files.html
- https://kilosort.readthedocs.io/en/latest/drift.html
- https://spikeinterface.readthedocs.io/en/latest/modules/sorters_internal.html
- https://spikeinterface.readthedocs.io/en/stable/modules/comparison.html
- https://pypi.org/project/mountainsort5/
