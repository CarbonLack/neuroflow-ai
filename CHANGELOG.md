# Changelog

## v0.5.1

- Added an explicit behavior/TTL import and clock-synchronization workflow with
  offset, drift, residual, missing-pulse, and unified-trial evidence.
- Added Neuropixels-like, tetrode, and independent-microwire simulation profiles
  with distinct contact geometry, behavior variables, TTL clocks, and ground truth.
- Added independent execution for event, spike-train, LFP, spike-field, and
  respiration analyses.
- Prevented unrun sorters and unrun workflow stages from displaying stale results.
- Kept the run status and progress bar fixed below the scrollable workspace.
- Routed wheel scrolling from non-scrollable workspace areas to the main page.
- Added per-sorter input/preprocessing/output contracts and probe-aware execution.
- Added packaged SVG, PDF, and PNG export self-tests and PyInstaller backend hooks.
- Expanded the bilingual workflow manual, synchronization schemas, sorter guidance,
  and source attribution.
- Added independent runtime tests for all six supported sorters and the normalized
  `neuroflow.sorting.v1` comparison contract.
