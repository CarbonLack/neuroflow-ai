# NeuroFlow sorter matrix

| Sorter | Execution | Typical use | Current Windows status |
|---|---|---|---|
| Kilosort4 | Native Python adapter | Neuropixels and dense silicon probes | Verified with CUDA |
| SpyKING CIRCUS 2 | SpikeInterface internal | General multichannel recording | Verified |
| Tridesclous2 | SpikeInterface internal | Low/medium channel counts | Verified |
| Simple | SpikeInterface internal | Fast teaching and smoke tests | Verified |
| Lupin | SpikeInterface internal | Native comparison workflow | Verified |
| MountainSort5 | SpikeInterface external Python package | Tetrodes and CPU workflows | Adapter integrated; build tool required on Windows/Python 3.12 |

## Detection rule

NeuroFlow never calls `spikeinterface.sorters.installed_sorters()` during startup.
That function probes every registered external backend, including unrelated MATLAB
and compiled tools. NeuroFlow probes only the six entries above and catches every
backend failure independently.

## Reproducibility

Every successful run stores sorter name, key, package version, execution backend,
result directory, Kilosort settings when applicable, and the run log in the
NeuroFlow project.

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
