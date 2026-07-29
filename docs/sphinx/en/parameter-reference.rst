Detailed controls and parameter reference
=========================================

This reference follows the 11-stage workbench. It explains what each operation does, why it is available, what output changes, how the default is chosen, and which checks must precede interpretation.

Defaults are starting points, not universal recipes. Acquisition metadata and study design take precedence.

01 Start with the data structure
--------------------------------

This page does more than select a file. NeuroEphys AI must know how each sample is stored, how many values form one time point, how probe contacts are arranged, and which device clock timestamps behavior. Those facts give filtering, sorting, and event alignment their correct physical units. Import keeps the source read-only and stores only links, caches, and derived results in the project.

01 · Before you start
~~~~~~~~~~~~~~~~~~~~~

Have the acquisition notes, sampling rate, total channel count, dtype, gain or µV/bit, probe geometry, and optional event CSV ready. For a generic binary file, copy values from the acquisition configuration rather than guessing from the traces.

01 · Page controls and visible consequences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

01 · Create an empty project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Choose a project name and location, then import data inside it.

**Purpose：** Separates source data from analysis products and creates a restore point.

**Visible result：** Creates neuroflow_project.json plus derived, results, and exports folders.

01 · Import generic binary
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Select .bin/.dat/.raw and enter rate, channels, dtype, and µV/bit.

**Purpose：** Reads interleaved recordings without self-describing metadata.

**Visible result：** Validates file size against channels × bytes per sample and displays traces.

01 · Import acquisition-system data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Choose Intan, Open Ephys, SpikeGLX, Blackrock, Plexon, TDT, or NWB.

**Purpose：** Uses a SpikeInterface extractor to read metadata and build a common cache.

**Visible result：** Stores a normalized int16 cache while leaving source files unchanged.

01 · Resume from existing sorting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Select Kilosort/Phy, IBL ALF, or an NWB file with Units.

**Purpose：** Skips unavailable raw stages and continues with units and downstream analyses.

**Visible result：** Produces normalized spike times in seconds, unit IDs, and provenance.

01 · Parameter-by-parameter explanation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

01 · Sampling rate
^^^^^^^^^^^^^^^^^^

**Meaning：** Samples per second; converts sample indices to seconds.

**Default：** Simulation: 30,000 Hz; device files: read from metadata

**Recommended setting：** Use the acquisition value exactly; extracellular spike recordings commonly use 20–30 kHz.

**Effect of changing it：** A low value stretches time and lowers frequencies; a high value compresses time and raises frequencies.

01 · Channel count
^^^^^^^^^^^^^^^^^^

**Meaning：** All channels stored per time point, including auxiliary channels in the file.

**Default：** Defined by the simulation electrode template

**Recommended setting：** Use the number physically written to the file, not merely the channels selected for sorting.

**Effect of changing it：** A wrong value reshapes the file and often creates repeated, shifted, or diagonal patterns.

01 · dtype
^^^^^^^^^^

**Meaning：** Storage type of each sample on disk.

**Default：** int16

**Recommended setting：** Read it from device metadata or export settings; never interpret float32 as int16.

**Effect of changing it：** A wrong dtype changes frame length and numeric interpretation; the file may open with invalid traces.

01 · µV / bit
^^^^^^^^^^^^^

**Meaning：** Microvolts represented by one integer ADC step.

**Default：** Generic import: 0.195; device import: read or normalize

**Recommended setting：** Use the acquisition gain; if unknown, keep ADC counts and mark units as unknown.

**Effect of changing it：** Affects amplitude units and amplitude-dependent thresholds, not spike sample locations.

01 · Copy source
^^^^^^^^^^^^^^^^

**Meaning：** Chooses a read-only link or a copied raw binary inside the project.

**Default：** Off: read-only link

**Recommended setting：** Use a link for stable storage; copy when the project must move or be archived independently.

**Effect of changing it：** Copying improves portability at a storage cost; links save space but fail if the source moves.

01 · Recommended operating order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Create a project first, then choose the entry that matches the files you actually have.
* Inspect 50–100 ms of traces and verify channel count, amplitude units, and duration.
* Save the project; reopening neuroflow_project.json should restore the page and workflow state.

01 · Frequent mistakes
~~~~~~~~~~~~~~~~~~~~~~

* Using 384 ephys channels as the file total when a sync channel is also stored.
* Moving an external source and expecting a read-only link to discover its new location.
* Expecting IBL ALF or Units-only NWB to provide raw voltage for re-sorting.

01 · Next step
~~~~~~~~~~~~~~

After confirming structure, continue to Raw QC; processed spikes begin at Unit QC.

**Method source：** SpikeInterface extractors; IBL ALF data model

02 Raw-signal quality control
-----------------------------

QC does not automatically delete channels. It builds evidence about where an anomaly occurs in channel, time, and frequency and whether it can affect referencing or spike detection. Locate problems globally, verify them in zoomed traces, and only then label candidate bad channels.

02 · Before you start
~~~~~~~~~~~~~~~~~~~~~

Verify sampling rate, channel count, units, and duration on the Data page.

02 · Page controls and visible consequences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

02 · Multichannel raw traces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Browse with time window, start time, channel range, and display gain.

**Purpose：** Find clipping, jumps, motion artifacts, dead channels, and common noise.

**Visible result：** Produces zoomable voltage snippets and RMS for the current window.

02 · QC metric summary
^^^^^^^^^^^^^^^^^^^^^^

**Action：** Run the sub-analysis and inspect RMS, peak-to-peak, clipping, and line-noise ratios.

**Purpose：** Screens channels using several metrics rather than one threshold.

**Visible result：** Creates a candidate bad-channel table without automatic exclusion.

02 · Channel-by-frequency power
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Inspect the channel-by-frequency power map and zoom suspicious bands.

**Purpose：** Distinguishes broadband noise, 50/60 Hz line noise, and local channel problems.

**Visible result：** Produces channel spectra and line-frequency evidence.

02 · Quality timeline
^^^^^^^^^^^^^^^^^^^^^

**Action：** Compute amplitude, noise, and clipping metrics in time blocks.

**Purpose：** Finds dropouts, drift, or artifacts limited to part of the session.

**Visible result：** Produces suspect intervals for exclusion or repair during preprocessing.

02 · Parameter-by-parameter explanation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

02 · Time start
^^^^^^^^^^^^^^^

**Meaning：** Start of the displayed recording window.

**Default：** 0 s

**Recommended setting：** Inspect the beginning, middle, end, and intervals around key task events.

**Effect of changing it：** Changes the view and local metrics without cropping the source.

02 · Window
^^^^^^^^^^^

**Meaning：** Duration displayed at once.

**Default：** 60 ms

**Recommended setting：** Use 20–100 ms for spikes and 1–10 s for slow artifacts or rhythms.

**Effect of changing it：** Short windows reveal waveforms; long windows reveal trends but compress spikes.

02 · Channel range
^^^^^^^^^^^^^^^^^^

**Meaning：** First channel and number shown together.

**Default：** Ch 0–11

**Recommended setting：** Inspect 8–16 channels at a time on dense probes and move along depth.

**Effect of changing it：** Too many channels reduce readability; too few can hide spatially shared patterns.

02 · Display gain
^^^^^^^^^^^^^^^^^

**Meaning：** Vertical display multiplier only.

**Default：** 1.0×

**Recommended setting：** Start at 1.0×, decrease for overlap, and increase for small traces.

**Effect of changing it：** Does not alter data or QC values; it only changes the view.

02 · Line frequency
^^^^^^^^^^^^^^^^^^^

**Meaning：** Center frequency for narrowband mains-power measurement.

**Default：** 50 Hz in China and most regions

**Recommended setting：** Choose 50 or 60 Hz for the recording location and inspect harmonics.

**Effect of changing it：** The wrong choice misses mains noise but does not alter the source.

02 · Recommended operating order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Run summary and timeline first, then verify every candidate in traces and spectra.
* Record evidence and the manual decision; do not delete channels directly on the QC page.
* Save QC decisions before preprocessing so bad channels do not contaminate referencing.

02 · Frequent mistakes
~~~~~~~~~~~~~~~~~~~~~~

* Confusing a high-firing channel with a noisy channel.
* Declaring the whole session good after inspecting only the first milliseconds.
* Applying a notch immediately without checking grounding, reference, and harmonics.

02 · Next step
~~~~~~~~~~~~~~

Carry confirmed bad channels and artifact intervals into separate AP and LFP preprocessing branches.

**Method source：** SpikeInterface preprocessing: detect_bad_channels, coherence+PSD, and channel grouping

03 Preprocessing is not a fixed recipe
--------------------------------------

More preprocessing is not automatically better. Every operation changes the signal, so its purpose, order, and duplication inside the sorter must be explicit. NeuroEphys AI previews a short segment first and compares traces and spectra before parameters are committed to the workflow.

03 · Before you start
~~~~~~~~~~~~~~~~~~~~~

Confirm bad channels and decide whether the target is AP/sorting, LFP, or both.

03 · Page controls and visible consequences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

03 · AP / sorting preview
^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Choose high-pass/band-pass, reference, and preview segment.

**Purpose：** Emphasizes fast action potentials and evaluates sorter input.

**Visible result：** Shows before/after traces, spectra, and RMS changes.

03 · LFP branch preview
^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Choose low-pass, downsampling, and line-noise handling.

**Purpose：** Preserves low-frequency population activity and reduces later computation.

**Visible result：** Creates an independent LFP chain without overwriting the AP branch.

03 · Reference comparison
^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Compare none, common median, and common average.

**Purpose：** Reduces common noise while checking whether bad-channel artifacts spread.

**Visible result：** Displays common components and channel traces before and after referencing.

03 · Commit processing chain
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Save operation order and parameters after reviewing the preview.

**Purpose：** Makes sorting, LFP, and reproducibility exports use the same traceable configuration.

**Visible result：** Stores the processing chain while the source remains read-only.

03 · Parameter-by-parameter explanation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

03 · AP band
^^^^^^^^^^^^

**Meaning：** Passband used for spike detection or preview.

**Default：** 300–6000 Hz

**Recommended setting：** Start with sorter/domain defaults and adjust only from sampling rate and spectral evidence.

**Effect of changing it：** A high lower cutoff suppresses broad spikes; a low one retains LFP drift. The upper cutoff must stay below Nyquist.

03 · LFP low-pass
^^^^^^^^^^^^^^^^^

**Meaning：** Highest retained LFP frequency.

**Default：** 300 Hz

**Recommended setting：** Use 150–250 Hz for analyses below 100 Hz; retain a higher cutoff and sampling rate for high-frequency oscillations.

**Effect of changing it：** Lower cutoffs smooth transients; overly high cutoffs allow spike leakage into LFP.

03 · LFP sampling rate
^^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Samples per second retained after LFP filtering.

**Default：** 1,000 Hz

**Recommended setting：** Keep at least twice the highest target frequency; 4–10× margin is common.

**Effect of changing it：** Too low causes aliasing or poor phase precision; too high increases memory and computation.

03 · Reference
^^^^^^^^^^^^^^

**Meaning：** Common reference estimate subtracted from each channel.

**Default：** Common median

**Recommended setting：** Start with median for dense recordings; use probe groups and reference design for sparse tetrodes or microwires.

**Effect of changing it：** Average is more sensitive to outliers; median is robust, but both can remove genuine common activity.

03 · Notch
^^^^^^^^^^

**Meaning：** Suppresses 50/60 Hz and optional harmonics.

**Default：** Off

**Recommended setting：** Enable only when QC shows narrowband contamination that cannot be corrected at acquisition.

**Effect of changing it：** Notching changes amplitude and phase around the target and can affect coupling analyses.

03 · Recommended operating order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Create separate AP and LFP branches rather than reusing one recipe.
* Preview before committing and retain raw, processed, and difference/spectral evidence.
* Check whether the sorter already filters, whitens, or corrects drift to avoid duplication.

03 · Frequent mistakes
~~~~~~~~~~~~~~~~~~~~~~

* Whitening both externally and inside Kilosort.
* Applying a global reference before excluding bad channels.
* Downsampling before low-pass filtering and causing aliasing.

03 · Next step
~~~~~~~~~~~~~~

Send the AP branch to Spike sorting and retain the LFP branch for neural analyses.

**Method source：** SpikeInterface PreprocessingPipeline, phase_shift, common_reference, and whitening

04 Spike sorting and tool selection
-----------------------------------

Spike sorting assigns candidate events in multichannel voltage to units. NeuroEphys AI preserves each sorter's native files, parameters, and logs while normalizing shared outputs into units, spike times in seconds, and channel/template descriptions for downstream comparison.

04 · Before you start
~~~~~~~~~~~~~~~~~~~~~

Confirm AP input, probe geometry, bad channels, hardware, output directory, and free disk space.

04 · Page controls and visible consequences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

04 · Select a sorter
^^^^^^^^^^^^^^^^^^^^

**Action：** Choose Kilosort4, MountainSort5, or another installed backend.

**Purpose：** Chooses an algorithm by probe density, hardware, and scientific need, not only availability.

**Visible result：** Loads that sorter's real settings and shows input preview before a run.

04 · Run selected sorter
^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Confirm data, sorter, parameters, and execution location in the dialog.

**Purpose：** Prevents expensive runs on the wrong data or configuration.

**Visible result：** Saves native output, normalized results, versions, settings, logs, and diagnostics.

04 · Inspect run diagnostics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Switch among drift, spike depth-time, amplitudes, templates, similarity, and logs.

**Purpose：** Assesses stability across time and probe depth.

**Visible result：** Produces sorting evidence required before Unit QC.

04 · Compare sorters
^^^^^^^^^^^^^^^^^^^^

**Action：** Activate different results and run unit matching and agreement comparison.

**Purpose：** Identifies consensus units, splits, merges, and sorter-specific units.

**Visible result：** Reports agreement on real data and accuracy only when simulation ground truth exists.

04 · Parameter-by-parameter explanation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

04 · Sorter
^^^^^^^^^^^

**Meaning：** Spike-sorting backend that will actually run.

**Default：** Kilosort4

**Recommended setting：** Evaluate Kilosort4 first for dense Neuropixels; compare CPU sorters for sparse/tetrode recordings.

**Effect of changing it：** Sorters differ in preprocessing, detection, clustering, and resources; they are not interchangeable parameter presets.

04 · n_chan_bin
^^^^^^^^^^^^^^^

**Meaning：** Total channels in the Kilosort binary, including channels not used for sorting.

**Default：** Read from the project structure

**Recommended setting：** Must match the physical file layout; Neuropixels 1.0 files commonly contain 385 channels.

**Effect of changing it：** A wrong value creates diagonal/repeated heatmaps and should stop the run immediately.

04 · batch_size
^^^^^^^^^^^^^^^

**Meaning：** Samples processed in each Kilosort batch.

**Default：** 60,000 (2 s at 30 kHz)

**Recommended setting：** Start with the default; for ≤64 channels, a longer batch can improve drift estimation.

**Effect of changing it：** Larger batches need more memory; short batches contain fewer spikes for drift estimation.

04 · nblocks
^^^^^^^^^^^^

**Meaning：** Number of depth blocks used for drift correction.

**Default：** 1 (rigid drift)

**Recommended setting：** Start at 1 for a single-shank Neuropixels probe, try 5 for non-rigid drift, and consider 0 for ≤64 sparse channels around ≥50 µm spacing.

**Effect of changing it：** Zero disables correction; too many blocks make sparse estimates unstable.

04 · Th_universal / Th_learned
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Detection thresholds for universal and learned templates.

**Default：** Current Kilosort4 default

**Recommended setting：** Start with defaults; lower by only 1–2 at a time when spikes are missed or units disappear.

**Effect of changing it：** Lower thresholds detect more events but increase noise and computation.

04 · tmin / tmax
^^^^^^^^^^^^^^^^

**Meaning：** Start and end times included in sorting.

**Default：** Full recording

**Recommended setting：** Crop only confirmed start/end artifacts and document the exclusion.

**Effect of changing it：** Short ranges speed testing but cannot establish full-session stability.

04 · duplicate_spike_ms
^^^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Window for removing near-duplicate spikes within a unit.

**Default：** Kilosort4 default

**Recommended setting：** Adjust only for a supported duplicate peak around zero in the ACG; never exceed 0.5 ms.

**Effect of changing it：** Large values corrupt refractory-period and ACG/CCG estimates.

04 · Recommended operating order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Run a representative segment with defaults to validate input and resources before the full session.
* Inspect Kilosort drift, depth-time, amplitude, template, and similarity views.
* Preserve native sorter directories; normalized output enables interoperability but does not replace native evidence.

04 · Frequent mistakes
~~~~~~~~~~~~~~~~~~~~~~

* Showing an old result from a different sorter when the selected sorter was not run.
* Calling cross-sorter agreement on real data accuracy.
* Comparing only unit counts while ignoring drift, duplicates, amplitudes, and logs.

04 · Next step
~~~~~~~~~~~~~~

Select an active sorting result and continue to Unit QC; return here when sorter comparison is needed.

**Method source：** Kilosort4; MountainSort5; SpikeInterface sorter and comparison modules

05 Unit QC and manual review
----------------------------

Sorter output contains candidate clusters. Unit QC combines firing rate, refractory-period evidence, SNR, waveforms, amplitude over time, and ACGs so the researcher can assign traceable keep, MUA, noise, or uncertain labels. No single threshold replaces review.

05 · Before you start
~~~~~~~~~~~~~~~~~~~~~

Confirm the active sorting result, run log, and drift diagnostics first.

05 · Page controls and visible consequences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

05 · Metric scatter and filters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Choose x/y metrics, thresholds, and labels; click a point to inspect a unit.

**Purpose：** Reveals metric tradeoffs and locates suspicious units.

**Visible result：** Produces a candidate subset without changing final labels automatically.

05 · Waveforms and templates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Inspect mean waveforms and variation on the main and neighboring channels.

**Purpose：** Assesses temporal stability, spatial plausibility, and noise.

**Visible result：** Produces unit-level waveform evidence.

05 · ACG and ISI
^^^^^^^^^^^^^^^^

**Action：** Zoom around 0 ms and inspect refractory violations and duplicate peaks.

**Purpose：** Evaluates contamination, duplicate spikes, and multi-unit mixtures.

**Visible result：** Produces temporal-structure evidence and refractory metrics.

05 · Manual decision
^^^^^^^^^^^^^^^^^^^^

**Action：** Label units good, MUA, noise, or uncertain and add a note.

**Purpose：** Preserves reviewer decisions and threshold versions for audit and revision.

**Visible result：** Outputs a traceable review table and downstream unit set.

05 · Parameter-by-parameter explanation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

05 · Firing rate
^^^^^^^^^^^^^^^^

**Meaning：** Spikes per second over valid recording time.

**Default：** Report only; no automatic exclusion

**Recommended setting：** Interpret with brain region, cell type, duration, and stability.

**Effect of changing it：** A higher minimum removes sparse units but can discard real low-rate cells.

05 · ISI violation window
^^^^^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Window used to count refractory-period violations.

**Default：** 2 ms

**Recommended setting：** Start around 1–2 ms and report the exact definition.

**Effect of changing it：** Larger windows count more violations; values are incomparable without the definition.

05 · SNR
^^^^^^^^

**Meaning：** Waveform signal magnitude relative to background noise.

**Default：** Report only

**Recommended setting：** Use one method consistently and inspect waveforms; do not transfer thresholds blindly across tools.

**Effect of changing it：** Higher thresholds are conservative but penalize real low-amplitude units.

05 · Amplitude stability
^^^^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Change in spike amplitude over time.

**Default：** Full-session timeline

**Recommended setting：** Look for decay, jumps, or brief presence and compare with drift diagnostics.

**Effect of changing it：** Overly strict criteria reject real state changes; loose criteria retain drifting or disappearing units.

05 · Contamination threshold
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Allowed estimated contamination.

**Default：** Not treated as ground truth

**Recommended setting：** If 10% is shown as a guide, report the estimator and review it with ACG and waveforms.

**Effect of changing it：** Lower thresholds reduce unit count and increase conservatism, but the estimate is itself uncertain.

05 · Recommended operating order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Inspect population distributions first, then review boundary and high-impact units.
* Thresholds create candidate labels; final decisions should record reviewer, time, and notes.
* Recompute QC after changing the active sorter; never reuse metrics from another result.

05 · Frequent mistakes
~~~~~~~~~~~~~~~~~~~~~~

* Declaring a good neuron from one SNR or ISI threshold.
* Reporting unit count as yield without the screening process.
* Changing labels manually without preserving an audit record.

05 · Next step
~~~~~~~~~~~~~~

After selecting downstream units, import behavior and TTL data and establish a common timeline.

**Method source：** SpikeInterface quality metrics; refractory-period contamination

06 TTL, behavior, and a common timeline
---------------------------------------

Behavior computers, cameras, and electrophysiology systems often have independent clocks. The synchronization page fits offset + slope × behavior_time from paired TTL pulses and uses residuals to detect missing pulses, mismatches, or nonlinear drift. Without matching TTLs, NeuroEphys AI can only assume a shared clock and labels that assumption explicitly.

06 · Before you start
~~~~~~~~~~~~~~~~~~~~~

Prepare behavior-event and optional TTL CSV files and identify each column's clock, unit, and event meaning.

06 · Page controls and visible consequences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

06 · Import behavior events
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Select a CSV with time_seconds, trial, condition, and event_type.

**Purpose：** Builds trial semantics and the event sequence in the behavior clock.

**Visible result：** Stores the event table and source path in the project.

06 · Import TTL pulses
^^^^^^^^^^^^^^^^^^^^^^

**Action：** Select a CSV containing ephys-clock pulses corresponding to behavior sync pulses.

**Purpose：** Creates an estimable mapping between device clocks.

**Visible result：** Shows matched counts, missing pulses, and duplicates.

06 · Fit common timeline
^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Pair pulses in order and fit intercept and slope.

**Purpose：** Corrects initial offset and linear clock drift.

**Visible result：** Produces ephys-clock seconds, residuals, drift ppm, and a trial table.

06 · Inspect synchronization evidence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Inspect residuals over time, event counts, and suspect pairs.

**Purpose：** Determines whether a linear map is adequate or pairing/segmentation must change.

**Visible result：** Preserves a synchronization report for every event-aligned analysis.

06 · Parameter-by-parameter explanation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

06 · Behavior time column
^^^^^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Column containing behavior-device timestamps.

**Default：** time_seconds

**Recommended setting：** Convert to seconds while retaining the source column; frame indices require frame rate or per-frame timestamps.

**Effect of changing it：** A unit mistake creates 1000× or sampling-rate-scale errors.

06 · TTL pairing
^^^^^^^^^^^^^^^^

**Meaning：** How behavior and ephys pulses are paired.

**Default：** Pair one-to-one in order

**Recommended setting：** Check counts and intervals first; locate missing pulses from interval patterns before pairing.

**Effect of changing it：** One missing pulse shifts all subsequent order-based pairs.

06 · Clock model
^^^^^^^^^^^^^^^^

**Meaning：** Function mapping behavior time to ephys time.

**Default：** offset + slope × time

**Recommended setting：** Start linear; use segmented or nonlinear models only for curved residuals or clock jumps.

**Effect of changing it：** An overly complex model fits pulse jitter; an overly simple model leaves systematic drift.

06 · Residual tolerance
^^^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Maximum allowed timing error after alignment.

**Default：** Report the observed value without hiding it

**Recommended setting：** Set from task timescale and device precision; millisecond spike responses require tighter limits.

**Effect of changing it：** Loose tolerance retains mismatches; strict tolerance rejects normal TTL jitter.

06 · Shared-clock assumption
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Whether behavior seconds are treated directly as ephys seconds without TTLs.

**Default：** Enabled with a warning only when TTLs are absent

**Recommended setting：** Use only with a shared hardware clock or externally completed synchronization.

**Effect of changing it：** Cannot detect offset or drift; the limitation must appear in the report.

06 · Recommended operating order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Inspect event/TTL counts and intervals before fitting.
* Residual plots must cover the full session, not only a mean error.
* Save the mapping, source columns, units, and excluded pairs in the project.

06 · Frequent mistakes
~~~~~~~~~~~~~~~~~~~~~~

* Treating behavior milliseconds as seconds.
* Forcing row-by-row pairing after a missing pulse.
* Reporting precise synchronization error without TTL evidence.

06 · Next step
~~~~~~~~~~~~~~

Use the synchronized trial table to inspect behavior before event-aligned neural analysis.

**Method source：** IBL synchronization and ALF trials object

07 Behavior quality precedes neural interpretation
--------------------------------------------------

Behavior analysis first asks whether the experiment ran as designed: trial counts per condition, choice balance, reaction times, missing values, and exclusions. Neural responses and machine-learning labels become interpretable only after behavior structure is reliable.

07 · Before you start
~~~~~~~~~~~~~~~~~~~~~

The synchronization page has produced a common timeline and trial table with start, event, and end definitions.

07 · Page controls and visible consequences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

07 · Condition counts
^^^^^^^^^^^^^^^^^^^^^

**Action：** Inspect trial counts by stimulus, choice, outcome, or group.

**Purpose：** Finds class imbalance and missing design cells.

**Visible result：** Outputs valid sample counts for statistics and decoding.

07 · Reaction time
^^^^^^^^^^^^^^^^^^

**Action：** Plot distributions, condition comparisons, and outlier trials.

**Purpose：** Identifies anticipatory responses, timeouts, and logging errors.

**Visible result：** Produces reaction-time variables and exclusion candidates.

07 · Psychometric curve
^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Compute choice probability and sample size by stimulus level.

**Purpose：** Checks whether behavior varies systematically with task variables.

**Visible result：** Outputs the curve, trial count per point, and fit parameters.

07 · Trial exclusions
^^^^^^^^^^^^^^^^^^^^^

**Action：** Flag missing, timeout, artifact, or outlier trials using predefined rules.

**Purpose：** Applies exclusions before neural results are viewed to reduce outcome-driven filtering.

**Visible result：** Retains every trial and an exclusion_reason rather than deleting rows.

07 · Parameter-by-parameter explanation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

07 · Condition column
^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Trial field used for group comparisons.

**Default：** condition

**Recommended setting：** Use original task labels and maintain a data dictionary.

**Effect of changing it：** Recoding changes groups and counts; preserve the mapping.

07 · Reaction-time start/end
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Two events defining reaction time.

**Default：** stimulus_onset → response

**Recommended setting：** Define from the scientific question; movement onset, button press, and reward are not interchangeable.

**Effect of changing it：** Different endpoints change both values and neural interpretation.

07 · Minimum trials
^^^^^^^^^^^^^^^^^^^

**Meaning：** Minimum valid trials required for a condition.

**Default：** Warning only; no automatic exclusion

**Recommended setting：** Use power analysis based on effect, variance, and validation design rather than one universal count.

**Effect of changing it：** Higher thresholds improve stability but exclude more sessions.

07 · Outlier rule
^^^^^^^^^^^^^^^^^

**Meaning：** Rule defining outliers in reaction time or continuous behavior.

**Default：** No deletion by default

**Recommended setting：** Prefer task-defined limits or robust rules and report excluded counts.

**Effect of changing it：** Post-hoc limits can change condition effects and introduce bias.

07 · Recommended operating order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Generate and save behavior figures before neural figures.
* Make every plotted point inspectable for stimulus level, count, and source trials.
* Store exclusion rules as fields and logs without overwriting the original trial table.

07 · Frequent mistakes
~~~~~~~~~~~~~~~~~~~~~~

* Reporting ordinary accuracy despite severe class imbalance.
* Changing behavioral exclusions after seeing neural differences.
* Confusing trial, session, and animal sampling levels.

07 · Next step
~~~~~~~~~~~~~~

After locking valid trials and condition labels, continue to event response, spike-train, LFP, or joint analyses.

**Method source：** IBL Brain-Wide Map behavioral analyses

08 Neural activity analysis workbench
-------------------------------------

The neural page is not a single fixed PSTH. It contains independently runnable event-response, spike-train, LFP spectral/time-frequency, and spike-field coupling analyses. Every sub-analysis has its own inputs, settings, figures, and tables; before execution it shows an input preview, never fabricated results.

08 · Before you start
~~~~~~~~~~~~~~~~~~~~~

Confirm active units, synchronized events, and valid trials; LFP and coupling also require voltage data.

08 · Page controls and visible consequences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

08 · Event-aligned Raster/PSTH
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Choose event, window, bin, smoothing, baseline, and condition.

**Purpose：** Describes unit or population responses around an event.

**Visible result：** Outputs raster, PSTH, heatmap, response windows, and trial-level features.

08 · Spike-train statistics
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Choose CV2, Lv, Fano, ACG/CCH, STTC, or spike-train distances.

**Purpose：** Quantifies regularity, variability, and temporal relationships between units.

**Visible result：** Produces metrics with explicit units and correlograms.

08 · LFP analysis
^^^^^^^^^^^^^^^^^

**Action：** Run PSD, band power, coherence, or time-frequency analysis.

**Purpose：** Describes oscillatory power, cross-channel relations, and event-related spectral changes.

**Visible result：** Outputs spectra, time-frequency matrices, band summaries, and method settings.

08 · Spike-field coupling
^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Choose phase band, reference channel, spike set, and surrogates.

**Purpose：** Tests whether spikes prefer an LFP phase and evaluates chance level.

**Visible result：** Outputs phase distributions, vector strength, Rayleigh/permutation evidence, and PAC/STA.

08 · Parameter-by-parameter explanation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

08 · Alignment event
^^^^^^^^^^^^^^^^^^^^

**Meaning：** Time zero for every trial.

**Default：** stimulus_onset (depends on the event table)

**Recommended setting：** Choose from the hypothesis; stimulus, movement, choice, and reward answer different questions.

**Effect of changing it：** Changing the event changes temporal interpretation and must not be significance-driven.

08 · Window
^^^^^^^^^^^

**Meaning：** Time range extracted around the event.

**Default：** -1 to +2 s

**Recommended setting：** Cover baseline and expected response while avoiding neighboring trials or events.

**Effect of changing it：** Short windows miss slow responses; long windows increase overlap and multiplicity.

08 · Bin size
^^^^^^^^^^^^^

**Meaning：** Temporal bin width for PSTH or count features.

**Default：** 50 ms

**Recommended setting：** Use 5–20 ms for fast sensory responses and 20–100 ms for behavioral/population trends, with sensitivity checks.

**Effect of changing it：** Small bins improve resolution but are noisy; large bins smooth responses and lower peaks.

08 · Smoothing
^^^^^^^^^^^^^^

**Meaning：** Kernel and width applied to binned firing rates.

**Default：** Minimal or off

**Recommended setting：** Smoothing is acceptable for display; statistics should prefer unsmoothed trial features and report the kernel.

**Effect of changing it：** Stronger smoothing lowers peaks, broadens responses, and induces temporal dependence.

08 · PSD method
^^^^^^^^^^^^^^^

**Meaning：** Power-spectral estimator and segmentation settings.

**Default：** Welch

**Recommended setting：** Start with Welch for stationary segments and report window, overlap, resolution, and units.

**Effect of changing it：** Long windows improve frequency resolution but reduce temporal localization, and vice versa.

08 · Surrogates
^^^^^^^^^^^^^^^

**Meaning：** Number of time shifts or label shuffles used for a chance distribution.

**Default：** 200 (demonstration)

**Recommended setting：** Use at least 1,000 for formal analysis and more for tail p-values; fix the random seed.

**Effect of changing it：** Fewer runs are faster but give coarse p-values; more runs are stable but expensive.

08 · Recommended operating order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Run one clearly defined sub-analysis at a time and review its input/settings summary first.
* Figures and statistics share trial, window, and condition definitions, while inference avoids display smoothing.
* Retain the data table behind every panel for independent editing and export.

08 · Frequent mistakes
~~~~~~~~~~~~~~~~~~~~~~

* Showing an old figure from another analysis before the new selection runs.
* Applying many pointwise t-tests directly to a smoothed PSTH.
* Downsampling LFP without anti-aliasing or allowing spike leakage in same-electrode coupling.

08 · Next step
~~~~~~~~~~~~~~

Send trial-level neural metrics to Statistics or build a trial-by-feature matrix for Machine Learning.

**Method source：** Neo data model; Elephant spike-train, spectral, STA and phase APIs; Folschweiller & Sauer (2023) case structure

09 From figures to statistical evidence
---------------------------------------

Statistics begins with the sampling unit, not a test name. Trials are nested in sessions and units in animals; pairing, repeated measures, and hierarchy determine valid comparisons. The page reports effects, confidence intervals, and multiplicity handling rather than treating p-values as the only result.

09 · Before you start
~~~~~~~~~~~~~~~~~~~~~

Prepare unsmoothed trial-level metrics, conditions, unit/session/animal IDs, and exclusions.

09 · Page controls and visible consequences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

09 · Design check
^^^^^^^^^^^^^^^^^

**Action：** Specify sampling unit, pairing, hierarchy, and primary comparison.

**Purpose：** Prevents pseudoreplication and treating nested samples as independent.

**Visible result：** Produces an auditable statistical-design summary.

09 · Parametric/nonparametric comparison
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Choose t/Welch/ANOVA or Wilcoxon/Mann–Whitney/Kruskal from the design.

**Purpose：** Compares conditions under explicit assumptions and data structure.

**Visible result：** Outputs statistic, p-value, effect, confidence interval, and sample size.

09 · Permutation/bootstrap
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Shuffle labels or resample at the legal exchangeability unit.

**Purpose：** Builds null distributions or intervals with fewer distributional assumptions.

**Visible result：** Saves random seed, repetitions, and the complete chance distribution.

09 · Mixed-effects model
^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Set fixed effects and animal/session/unit random effects.

**Purpose：** Handles hierarchical, missing, and unbalanced repeated measures.

**Visible result：** Outputs formula, coefficients, intervals, convergence, and diagnostics.

09 · Parameter-by-parameter explanation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

09 · Sampling unit
^^^^^^^^^^^^^^^^^^

**Meaning：** Independent observational unit used for inference.

**Default：** Must be confirmed by the user

**Recommended setting：** Animal-level claims usually require animals as independent units, with units/sessions nested.

**Effect of changing it：** Too fine inflates n and significance; too coarse loses information.

09 · Paired
^^^^^^^^^^^

**Meaning：** Whether conditions come from the same or matched observational unit.

**Default：** Defined by the study design

**Recommended setting：** Use paired tests for repeated observations from the same unit/session/animal.

**Effect of changing it：** Incorrect pairing changes the error term and statistical power.

09 · Alpha
^^^^^^^^^^

**Meaning：** Predefined type-I error threshold.

**Default：** 0.05

**Recommended setting：** Set before analysis and report together with multiplicity correction.

**Effect of changing it：** Lower alpha is conservative but increases misses; never change it post hoc for significance.

09 · Multiple comparison
^^^^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Method controlling error across a family of tests.

**Default：** FDR Benjamini–Hochberg

**Recommended setting：** Use FDR for exploratory multi-unit/time tests and Holm for a few planned comparisons; define the family.

**Effect of changing it：** Stricter correction reduces false positives and power; correction is meaningless without a defined family.

09 · Resamples
^^^^^^^^^^^^^^

**Meaning：** Number of permutation or bootstrap repetitions.

**Default：** 1,000

**Recommended setting：** Use 200–1,000 for preview and often 5,000–10,000 for final estimates with a fixed seed.

**Effect of changing it：** Controls Monte Carlo stability of p-values/intervals and runtime.

09 · Recommended operating order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Create a statistical-design card before enabling test selection.
* Report raw observations, effect, confidence interval, p-value, and correction together.
* Save the full statistical table separately from figure summaries.

09 · Frequent mistakes
~~~~~~~~~~~~~~~~~~~~~~

* Treating 300 units from three animals as n=300 independent observations.
* Testing every PSTH bin without multiplicity control.
* Reporting only p-values without direction, magnitude, or uncertainty.

09 · Next step
~~~~~~~~~~~~~~

Statistical results can go to publication export; prediction questions continue to Machine Learning.

**Method source：** SciPy/statsmodels; Elephant phase analysis; Folschweiller & Sauer (2023) statistical design

10 Machine learning, clustering, and leakage
--------------------------------------------

Machine Learning converts neural activity to a trial-by-feature matrix and places preprocessing, feature selection, and the model inside cross-validation. The goal is not the highest score but a leakage-free evaluation against a shuffle baseline with session/animal generalization.

10 · Before you start
~~~~~~~~~~~~~~~~~~~~~

Define prediction target, feature window, grouping variable, class balance, and minimum sample size.

10 · Page controls and visible consequences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

10 · Classification
^^^^^^^^^^^^^^^^^^^

**Action：** Choose Logistic regression, SVM, Random forest, XGBoost, or another model.

**Purpose：** Predicts discrete stimulus, choice, or outcome labels.

**Visible result：** Outputs balanced accuracy, F1, AUC, confusion matrix, and fold scores.

10 · Regression
^^^^^^^^^^^^^^^

**Action：** Choose linear, Ridge, random-forest, or another regressor.

**Purpose：** Predicts position, speed, reaction time, or continuous stimulus values.

**Visible result：** Outputs R², MAE, predicted-versus-observed plots, and residuals.

10 · Time-resolved decoding
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Repeat the complete cross-validation inside sliding time bins.

**Purpose：** Estimates how predictive information changes around an event.

**Visible result：** Outputs a time course, chance distribution, and multiplicity results.

10 · PCA and clustering
^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Reduce population features or perform unsupervised grouping.

**Purpose：** Explores population structure without treating visual separation as inference.

**Visible result：** Outputs explained variance, loadings, projections, and clustering stability.

10 · Parameter-by-parameter explanation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

10 · Feature window
^^^^^^^^^^^^^^^^^^^

**Meaning：** Time range used to extract neural features for each trial.

**Default：** 0–0.5 s (task-dependent)

**Recommended setting：** Predefine from causal timing; do not use post-behavior information to predict behavior.

**Effect of changing it：** Long windows contain more information but can include later events and movement.

10 · Cross-validation
^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Train/validation split and repetition scheme.

**Default：** 5-fold stratified or grouped

**Recommended setting：** Use GroupKFold or LeaveOneGroupOut when sessions or animals must not cross folds.

**Effect of changing it：** Random trial splits often score higher but may learn session identity.

10 · Scaling
^^^^^^^^^^^^

**Meaning：** Feature standardization or normalization.

**Default：** StandardScaler for linear/SVM models

**Recommended setting：** Fit within every training fold and apply to its validation fold.

**Effect of changing it：** Scaling the full dataset first leaks validation means and variances.

10 · Class weighting
^^^^^^^^^^^^^^^^^^^^

**Meaning：** Loss weights for imbalanced classes.

**Default：** balanced (for imbalanced classes)

**Recommended setting：** Report class counts first; weighting or resampling must occur inside training folds.

**Effect of changing it：** Changes decision boundaries and calibration; ordinary accuracy is insufficient.

10 · Permutation count
^^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Number of label shuffles with complete re-validation.

**Default：** 200 (demonstration)

**Recommended setting：** Use at least 1,000 for final results while preserving group structure.

**Effect of changing it：** One shuffle is unstable; invalid shuffling destroys nesting.

10 · Recommended operating order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Establish a linear baseline before comparing complex models.
* Place the model, feature selection, scaling, and hyperparameter search inside validation.
* Report fold scores, shuffle distribution, and cross-group generalization rather than one best score.

10 · Frequent mistakes
~~~~~~~~~~~~~~~~~~~~~~

* Putting adjacent trials from the same session into both train and test.
* Selecting units on all data before cross-validation.
* Showing only the best model after undisclosed model comparison.

10 · Next step
~~~~~~~~~~~~~~

Send model configuration, validation splits, score tables, and figures to Publication and Reproducibility.

**Method source：** IBL Brain-Wide Map decoding analyses; scikit-learn

11 Publication figures and reproducible export
----------------------------------------------

Export binds figures to plotted data, statistical tables, Methods, the software environment, and the workflow. Visual edits never rewrite analysis data; recomputation and styling have separate audit trails. A saved neuroflow_project.json restores completed stages and the active result.

11 · Before you start
~~~~~~~~~~~~~~~~~~~~~

Verify axes, units, sample sizes, error definitions, and annotations against saved results.

11 · Page controls and visible consequences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

11 · Edit current figure
^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Double-click an axis or open Figure Studio for object-level styling.

**Purpose：** Creates publication styling without recomputing data.

**Visible result：** Edits lines, markers, bars, images, text, axes, ticks, grids, and legends.

11 · Save one panel
^^^^^^^^^^^^^^^^^^^

**Action：** Select a panel, set exact dimensions, and export it.

**Purpose：** Avoids screenshots with poor resolution and layout.

**Visible result：** Exports PNG, SVG, or PDF with background and font settings.

11 · Export data and statistics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Save x/y/group data behind the figure and the complete statistical output.

**Purpose：** Links the figure back to values and enables external verification.

**Visible result：** Exports CSV/JSON tables and a provenance index.

11 · Save/restore project
^^^^^^^^^^^^^^^^^^^^^^^^^

**Action：** Save the project, then reopen neuroflow_project.json from the home page.

**Purpose：** Restores sources, workflow state, sorter results, analysis tables, and audit log.

**Visible result：** Reopens at the last saved page with completed stages available for inspection.

11 · Parameter-by-parameter explanation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

11 · Format
^^^^^^^^^^^

**Meaning：** Figure file type.

**Default：** PNG + SVG

**Recommended setting：** Use PNG for preview and SVG/PDF for vector editing and publication.

**Effect of changing it：** Raster output depends on DPI; vector output preserves line and text objects.

11 · Figure size
^^^^^^^^^^^^^^^^

**Meaning：** Output width and height.

**Default：** Use the current figure

**Recommended setting：** Set journal single/double-column dimensions in millimeters and inspect long labels.

**Effect of changing it：** Changing dimensions alters relative text size and panel spacing.

11 · DPI
^^^^^^^^

**Meaning：** Pixels per inch for raster output.

**Default：** 300

**Recommended setting：** Use 300–600 DPI for line art and follow journal/source resolution for images or heatmaps.

**Effect of changing it：** Higher DPI increases file size but cannot add source-data resolution.

11 · Axis/grid/spine
^^^^^^^^^^^^^^^^^^^^

**Meaning：** Axis line width, extent, ticks, grid, and spine visibility.

**Default：** NeuroEphys AI standard theme

**Recommended setting：** Adjust by plot type and keep a figure consistent; do not let decorative grids obscure data.

**Effect of changing it：** Thick lines improve visibility but crowd small panels; strong grids compete with data.

11 · Project source mode
^^^^^^^^^^^^^^^^^^^^^^^^

**Meaning：** Whether the project uses an external read-only link or an internal raw copy.

**Default：** Defined by the import choice

**Recommended setting：** Before archiving, verify external paths; copy raw data or use stable shared storage for portability.

**Effect of changing it：** The manifest remains readable, but raw-dependent stages cannot rerun if an external source is missing.

11 · Recommended operating order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Save vector output, plotted data, statistical tables, and generation settings for every publication figure.
* After saving, close and reopen once to verify restore position and key results.
* Before sharing, check source paths, licenses, anonymization, and unpublished-data permissions.

11 · Frequent mistakes
~~~~~~~~~~~~~~~~~~~~~~

* Saving only screenshots without plotted data or statistical provenance.
* Editing labels until units or sample counts no longer match results.
* Treating a project linked to a personal temporary folder as a portable archive.

11 · Next step
~~~~~~~~~~~~~~

After the reproducibility bundle, the researcher remains responsible for interpretation, manuscript structure, and data-sharing decisions.

**Method source：** IBL Brain-Wide Map figure organization and reproducibility
