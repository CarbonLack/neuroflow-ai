# NeuroEphys AI 1.4.0 validation record

Status: local release validation passed. This file is updated only with completed checks.

## Completed checks

- 2026-09-23: SpikeInterface 0.104.8 SortingAnalyzer smoke test completed all
  10 requested extensions on a local short recording; no extension failed.
- 2026-09-23: continuous Unit-ID normalization round-tripped through project save/load,
  including NEX5 imported native cluster 0 → display Unit 1 provenance.
- 2026-09-23: all-spike PCA/waveform collection, lasso-edit data model, nested split
  undo, and curated downstream cohort tests passed.
- 2026-09-23: trace controls were found to have a Qt signal-argument mismatch; the
  defect was fixed and an interaction regression test now covers all five controls.
- 2026-09-23: native publication gallery test confirmed multiple SVG cards in one
  vertically scrollable document.
- 2026-09-23: three 60-second local teaching projects completed import-equivalent raw
  data creation, QC, preprocessing, imperfect benchmark detection, Unit metrics,
  synchronization, event analysis, neural toolkit, statistics, decoding, and export.
  Fixed-seed AUC values were 0.764 (Neuropixels-like), 0.668 (tetrode), and 0.898
  (independent microwire); none was perfect.
- 2026-09-23: publication composites were inspected after removing escaped dashboard
  suptitles and replacing the meaningless one-sorter self-agreement panel with a
  per-Unit F1 distribution.
- 2026-09-23: the complete local regression suite passed: 206 tests passed. The
  remaining console messages are dependency deprecation/runtime warnings rather
  than failed assertions.
- 2026-09-23: English and Chinese Sphinx manuals rebuilt successfully. The manual
  audit checked 57 pages and 9,087 local links with zero errors.
- 2026-09-23: the product screenshot workflow completed in both languages; teaching
  screenshots identify simulated detector outputs honestly rather than presenting
  them as Kilosort or MountainSort executions.
- 2026-09-23: Standard and Full Windows builds completed. The release directory
  contains the Standard installer and portable ZIP, Full selectable installer and
  local Full portable ZIP, Python wheel/source archive, documentation, and SHA-256
  checksums.
- 2026-09-23: the copied canonical Full portable executable passed startup, AI,
  figure-export, MountainSort5, internal-sorter, and Kilosort4 packaged self-tests.
- 2026-09-23: the 11-slide roadshow deck completed five render-and-inspect review
  rounds, package/layout/font validation, and an eight-minute speaker-note timing
  audit.
- 2026-09-23: the synchronized roadshow speaker script was generated in DOCX and
  Markdown. The DOCX rendered to 16 pages; every page was visually inspected with
  no clipping, overflow, or cross-page layout defect. Slide timings total exactly
  8:00 and the document includes a fallback demo route and judge Q&A.

## Pending online verification

- Final GitHub release-asset verification.
