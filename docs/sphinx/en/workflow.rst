Complete workflow
=================

The eleven stages form a recoverable sequence. Each stage can also be opened
independently when its required input already exists.

01 Data and project
-------------------

Verify the recording structure and scientific metadata. A wrong channel count
reshapes binary data incorrectly; a wrong sampling rate changes every time
conversion.

02 Raw QC
---------

Inspect zoomable traces, channel RMS, saturation, line-noise evidence,
channel-frequency summaries, and quality over time. Automatic flags are
screening evidence. They do not remove channels without a recorded user
decision.

03 Preprocessing
----------------

Preview a short segment before processing a long record. The spike branch
exposes filtering and referencing choices. The LFP branch is enabled only when
low-frequency content exists in the acquisition.

04 Spike sorting
----------------

Choose a sorter explicitly, inspect its native parameters, confirm the runtime
environment, and launch it. The selected backend, version, parameters, start
time, end time, logs, and native output path enter the audit record.

05 Unit QC
----------

Review waveforms, autocorrelograms, refractory-period violations, amplitude
stability, firing rate, SNR, and duplicate/split risk. Label each candidate as
accepted single unit, multi-unit activity, noise, or uncertain. Sorting output
alone does not establish a biological single unit.

06–07 Synchronization and behavior
----------------------------------

Map event codes, compare behavioral and electrophysiology clocks, quantify
residuals and missing pulses, construct the trial/event table, and inspect
condition balance and reaction time.

08 Neural analysis
------------------

Choose alignment events and windows. Generate per-unit raster and PSTH,
population heatmaps, spike-train statistics, or supported LFP analyses.

09–10 Statistics and decoding
-----------------------------

Define the sampling unit and comparison before choosing a test. Decoding uses
cross-validation and label permutation; session, animal, and unit structure
must remain visible to prevent leakage or pseudoreplication.

11 Publication and reproducibility
----------------------------------

Export editable SVG/PDF/PNG figures, source tables, Methods text, environment
versions, workflow settings, audit logs, and the saved project manifest.
