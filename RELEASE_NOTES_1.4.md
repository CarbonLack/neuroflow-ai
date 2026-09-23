# NeuroEphys AI 1.4.1

## 1.4.1 reliability and readability fixes

- OpenAI-compatible Chat endpoints, including the institute DeepSeek V4.1
  gateway, receive portable non-strict tool declarations. Strict calling
  requires a backend-specific opt-in; proposed actions remain locally
  schema-validated and require researcher confirmation.
- HTTP 400 model errors now identify request-format incompatibility instead of
  incorrectly suggesting that the project, key, or account quota failed.
- AI conversation bubbles use the full available sidebar width and measure rich
  text after layout, so long replies remain readable rather than clipped.
- The in-app publication gallery keeps its figure and captions readable under
  the dark application theme and avoids horizontal overflow at narrow widths.

## 1.4.0 feature set

## Researcher-controlled Unit curation

- The review workspace renders every readable spike waveform and PCA point rather
  than a small display sample.
- Lasso selection can exclude outlier spikes or split one current cluster into a
  new Unit. Edits are revisioned, undoable, and never overwrite native sorter output.
- Downstream analysis can be restricted to manually reviewed candidate single
  Units. Changing a label invalidates the applied cohort until it is reapplied.
- NeuroEphys AI uses continuous one-based Unit IDs in plots and tables while
  preserving native sorter cluster IDs in provenance.

## Publication figures and plotted data

- Step 11 is a native, continuous vertical manuscript gallery with visibly separate
  main and Extended Data figures, editable captions, panel ordering, and assignment.
- Every panel retains its original SVG, plotted JSON/NPZ data, source analysis, and
  provenance. The gallery uses vector SVG instead of a blurred webpage screenshot.
- Main figures follow measurement/QC → behavior/events → Unit/population response →
  uncertainty/decoding. Every other exported result remains in Extended Data.
- Event rasters use classic colored tick marks and separate behavior-condition rows.

## Analysis and usability

- The sorter catalog now documents eleven integrations and distinguishes bundled
  runnable backends from optional MATLAB/runtime dependencies.
- SpikeInterface SortingAnalyzer postprocessing computes available waveforms,
  templates, amplitudes, locations, correlograms, similarity, PCA, and quality metrics.
- Long runs expose measured stage progress plus safe pause/resume/cancel controls;
  mutating navigation is locked while a worker updates project state.
- Trace time, channel, count, and gain controls now reliably refresh the figure.
- Behavior palettes remain deterministic and non-repeating for large repertoires.

## Local teaching projects

Three self-contained 60-second projects cover a Neuropixels-like probe, four
tetrodes, and 32 independent brush/microwire contacts. Their detector outputs are
explicitly labeled synthetic and imperfect, with misses, false positives, jitter,
and slight cross-Unit leakage. No published recording is downloaded or bundled.

## Release delivery

- GitHub provides the recommended Full selectable installer, Standard installer,
  Standard portable ZIP, Python artifacts, checksums, the reviewed roadshow deck,
  and synchronized DOCX/Markdown speaker scripts.
- The 3.13 GB Full portable ZIP is retained in the canonical local release archive
  because it exceeds GitHub's 2 GiB per-asset limit; it contains the same Full runtime
  payload available through the selectable Full installer.
