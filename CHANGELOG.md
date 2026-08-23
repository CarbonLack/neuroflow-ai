# Changelog

## Unreleased

- Simplified the home screen to a centered, single-background entry area with
  New project, Open/import project, and one combined Example projects library
  for simulations and verified public data.
- Added standard File, Edit, View, Analysis, and Help menus with keyboard
  shortcuts for common project and workflow actions.
- Added a linear stage strip with Previous/Next navigation and compact,
  first-visit step guides that can be disabled or reset.
- Rebuilt the workspace as a resizable three-column splitter. The workflow rail
  can compact to stage numbers, the AI/help/audit column remains available on
  the right, and narrow windows preserve analysis content through adaptive
  sizing and scrolling.
- Preserved the existing purple-black visual identity while improving hierarchy
  and reducing fixed minimum sizes for smaller windows.

## v1.1.0

- Added generic single-trial population analysis with explicit event/unit scopes,
  configurable binning and Gaussian smoothing, per-trial validity masks,
  pooled/per-trial baseline handling, peak/PCA/optional Rastermap ordering,
  condition views, and PCA trajectories.
- Added trial-held-out continuous-signal regression with explicit neural-to-target
  lag and repeated neuron-count scaling.
- Added auditable fine-timing connectivity with three CCG normalizations,
  interval/centered jitter, flank-SD/empirical inference, multiplicity control,
  region/distance filtering, deterministic pair sampling, and workload estimates.
- Exposed the new methods through the desktop App, stable Python API, reproducible
  export bundle, and `neuroephys population` / `neuroephys connectivity` commands.
- Validated the generic single-trial implementation on the public Trautmann et al.
  (2025) Fig. 7 LIP/SC data with pointwise agreement above r=0.998.

## v1.0.0

- Added the stable `neuroephys` Python API, lazy public exports, command-line
  environment inventory, deterministic demo creation, and offline self-tests.
- Added Python wheel/sdist metadata with optional desktop, MountainSort5, and
  Kilosort components while preserving the internal `neuroflow` import path.
- Unified the application, project manifest, exported provenance, documentation,
  and distribution metadata at version 1.0.0.
- Separated the installed application from the writable user workspace and added
  a `NEUROEPHYS_HOME` override for managed laboratory computers.
- Added formal Windows portable and per-user installer release paths, first-read
  instructions, checksums, and release verification contracts.

## v0.8.0

- Added an optional cloud AI assistant without changing the manual or guided
  analysis main line.
- Added OpenAI Responses API and OpenAI-compatible Chat API providers with a
  configurable endpoint, model, reasoning effort, and session-only API key.
- Added four bounded AI tasks: explain the current stage, review project status,
  propose a candidate workflow, and explain the latest error.
- Added a path-free project summary, explicit cloud-data preview, raw-voltage
  exclusion, sensitive-text redaction, and opt-in audit-log context.
- Constrained structured workflow plans to NeuroEphys AI's 11 registered stages and
  rejected unknown stages before they reach the interface.
- Kept every AI plan advisory: applying a plan requires confirmation, stores it
  as `advisory_not_executed`, and never runs or replaces an analysis result.
- Persisted AI answers and accepted plans in the project audit history while
  keeping API keys out of projects and application settings.
- Added a bilingual AI manual covering setup, tasks, privacy fields, confirmation
  boundaries, model choices, failure handling, and official API sources.
- Added network-contract, redaction, project roundtrip, and UI non-execution tests.

## v0.7.0

- Rebuilt the in-app tutorial center around 11 detailed, bilingual chapters. Each
  chapter now explains its scientific purpose, prerequisites, operations,
  parameter meanings, defaults, recommended starting points, parameter effects,
  common mistakes, acceptance checks, sources, and the next stage.
- Reorganized the product manual into separate Chinese and English sites with a
  Kilosort-inspired information architecture: introduction, installation, GUI
  guide, complete tutorials, data inputs, sorting, parameters, Figure Studio,
  troubleshooting, and sources.
- Moved the selected-analysis action into the fixed progress footer so it remains
  available while scrolling through long figures, tables, and sorter diagnostics.
- Added a Save/Discard/Cancel close guard for unsaved projects and blocked closing
  during an active analysis to protect partially completed work.
- Upgraded the project schema to persist preprocessing and analysis results in
  addition to source paths, sorting archives, QC, statistics, decoding,
  workflow status, and audit logs.
- Restored the last saved workflow stage when reopening a project, allowing
  researchers to continue from the previous checkpoint rather than restart.
- Added regression tests for project resume, unsaved-close saving, fixed run
  controls, detailed tutorial coverage, and monolingual English parameters.

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
