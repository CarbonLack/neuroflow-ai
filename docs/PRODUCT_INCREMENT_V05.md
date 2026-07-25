# NeuroFlow v0.5 product increment

## Main line retained

NeuroFlow remains a local-first, modular and explainable desktop workbench:

`import -> raw QC -> preprocessing -> sorting -> unit QC -> synchronization ->
behavior -> neural analysis -> statistics -> machine learning -> publication`

Manual control, guided operation and optional AI assistance remain separate. No
analysis depends on a language model.

## Added depth

- Raw QC now includes channel-frequency power and a recording-wide quality
  timeline instead of a single summary panel.
- Preprocessing is shown as separate AP/sorting and LFP branches with an
  auditable chain and explicit safeguards.
- Unit review adds mean waveform, ACG, ISI and time/amplitude stability per unit.
- Neo adapters preserve units and time metadata for spike and analog objects.
- Elephant runs rate/interval, Fano, CCH, STTC, distance, PSD, coherence and
  spike-phase analyses.
- A synthetic respiration case demonstrates a paper-derived analysis structure
  without using or imitating the paper's figures.
- Statistics adds sampling-hierarchy guidance and circular/surrogate evidence.
- The application opens a local bilingual documentation site.
- The central analysis workspace scrolls independently and reserves a large,
  stable canvas for scientific figures. Every subplot can be selected, expanded,
  edited, inspected, and exported independently as SVG, PDF, or 300 dpi PNG.

## Honest capability boundary

The advanced Elephant pattern-detection catalog is visible as future work, not
misrepresented as validated one-click analysis. The respiration case is explicitly
labelled as synthetic method validation. Imported projects without raw voltage can
still run spike-train analyses while LFP and spike-field stages report why they were
skipped.
