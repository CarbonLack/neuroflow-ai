# Changelog

## v0.6.1

- Separated empty-project creation from data import. An empty project now opens
  a dedicated Data and project panel with explicit own-data, public-project, and
  teaching-simulation actions.
- Replaced the generic public-data home action with two fixed, versioned,
  locally discoverable IBL and Buzsáki validation projects that open from a
  status-aware project library.
- Extended Figure Studio with exact X/Y axis lengths, plot position, independent
  spines, major/minor ticks, number formatting, independent X/Y grids, custom
  reference lines, and detailed legend-frame controls.
- Added run confirmation, completion-summary, and failure dialogs while
  retaining the persistent audit log and fixed progress footer.
- Expanded the data-entry and Figure Studio manuals with the new controls and
  official GraphPad Prism interaction references without copying its code or UI.

## v0.6.0

- Replaced the opaque home data list with five task-oriented entry routes that
  state what to select, where the workflow starts, whether sorting is available,
  and what happens downstream.
- Added a generic processed-NWB Units importer with behavior events, position,
  sleep-state, and ripple-interval support.
- Added repeatable public-data validation scripts for an exact IBL Brain-Wide Map
  ALF session and Buzsáki Lab DANDI 000552 NWB session.
- Added object-level Figure Studio editing for whole-figure properties, axes,
  lines, scatters, patches, images, text, legends, and multi-format export, with
  an embedded live preview.
- Added dedicated manuals for all 11 workflow stages, five data routes, Figure
  Studio, and public validation, including parameter effects, failure signals,
  quality checks, and source attribution.
- Made long documentation tables scroll locally on narrow screens and verified
  every documentation page at desktop and mobile widths.
- Hardened statistics against constant-response and zero-variance real datasets
  by recording non-testable states instead of crashing.

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
