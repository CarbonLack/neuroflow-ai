# NeuroFlow sorter matrix

| Sorter | Execution | Typical use | Current Windows status |
|---|---|---|---|
| Kilosort4 | Native Python adapter | Neuropixels and dense silicon probes | Verified with CUDA |
| SpyKING CIRCUS 2 | SpikeInterface internal | General multichannel recording | Verified |
| Tridesclous2 | SpikeInterface internal | Low/medium channel counts | Verified |
| Simple | SpikeInterface internal | Fast teaching and smoke tests | Verified |
| Lupin | SpikeInterface internal | Native comparison workflow | Verified |
| MountainSort5 | SpikeInterface external Python package | Tetrodes and CPU workflows | Integrated; `isosplit6` is compiled during the Windows release build |

## Detection rule

NeuroFlow never calls `spikeinterface.sorters.installed_sorters()` during startup.
That function probes every registered external backend, including unrelated MATLAB
and compiled tools. NeuroFlow probes only the six entries above and catches every
backend failure independently.

## Reproducibility

Every successful run stores sorter name, key, package version, execution backend,
result directory, Kilosort settings when applicable, and the run log in the
NeuroFlow project.

Every sorter is converted to the same `neuroflow.sorting.v1` contract:

- integer Unit identifiers;
- monotonically increasing spike times in seconds;
- acquisition sampling rate;
- sorter name and version;
- parameters, backend, source directory, Unit count, and spike count.

Native files remain intact. The normalized view is what downstream Unit QC,
event alignment, statistics, and plotting consume.

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
