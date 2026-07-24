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
