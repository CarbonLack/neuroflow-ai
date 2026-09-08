Controls and method parameters
================================================================================

The operating steps below share the App's task catalogue. Method parameters explain the underlying tools; not every parameter is adjustable in the desktop interface. Reference values are not a guarantee of the current App or sorter default. Use the settings and saved run record for your selected analysis.

:doc:`task-guide`

Import a raw recording
----------------------------------------------------------------------------------------------------

Create a project from acquisition files or generic binary, then check recording metadata and traces.

**Have ready**

Recording files, sampling rate, channel count, dtype, gain, and probe information. Acquisition files often supply some metadata.

1. **Choose an input**

   Click New project on the home page and select acquisition files or generic binary. In an open empty project, use Data and project → Import my electrophysiology data.

2. **Verify reading parameters**

   Select the acquisition reader. For .bin/.dat, verify rate, channels, dtype, and μV/bit, including values detected from params.py. Open Ephys attempts AP selection when no stream is specified.

3. **Inspect the imported recording**

   Check the source, duration, and channel count in Data and project. Move through the trace time window and verify channels before opening Raw QC.

**Check the result**

Check parameters against the acquisition software. An incorrect rate or channel count distorts timing and traces.

**Saved output**

The project stores source links, reading parameters, and available caches. Find them with File → Open project folder.

01 · Sampling rate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Samples per second; converts sample indices to seconds.

**Reference value:** Simulation: 30,000 Hz; device files: read from metadata

**Method considerations:** Use the acquisition value exactly; extracellular spike recordings commonly use 20–30 kHz.

**Effect:** A low value stretches time and lowers frequencies; a high value compresses time and raises frequencies.

01 · Channel count
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** All channels stored per time point, including auxiliary channels in the file.

**Reference value:** Defined by the simulation electrode template

**Method considerations:** Use the number physically written to the file, not merely the channels selected for sorting.

**Effect:** A wrong value reshapes the file and often creates repeated, shifted, or diagonal patterns.

01 · dtype
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Storage type of each sample on disk.

**Reference value:** int16

**Method considerations:** Read it from device metadata or export settings; never interpret float32 as int16.

**Effect:** A wrong dtype changes frame length and numeric interpretation; the file may open with invalid traces.

01 · µV / bit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Microvolts represented by one integer ADC step.

**Reference value:** Generic import: 0.195; device import: read or normalize

**Method considerations:** Use the acquisition gain; if unknown, keep ADC counts and mark units as unknown.

**Effect:** Affects amplitude units and amplitude-dependent thresholds, not spike sample locations.

01 · Copy source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Chooses a read-only link or a copied raw binary inside the project.

**Reference value:** Off: read-only link

**Method considerations:** Use a link for stable storage; copy when the project must move or be archived independently.

**Effect:** Copying improves portability at a storage cost; links save space but fail if the source moves.

`Method documentation <https://spikeinterface.readthedocs.io/en/latest/modules/extractors.html>`__

Inspect traces and channel quality
----------------------------------------------------------------------------------------------------

Use traces, power maps, and a timeline to identify noisy channels and periods.

**Have ready**

A project with readable raw voltage.

1. **Run Raw QC**

   Open Raw QC and click Run selected analysis. Wait for completion in the bottom status area.

2. **Switch diagnostic views**

   Use the dropdown beside the title to inspect QC metric summary, Channel-by-frequency power, and Quality timeline.

3. **Verify with traces**

   Return to Multichannel raw traces and adjust the time window and channels. Verify noise, clipping, or suspicious periods and record decisions in the project notes.

**Check the result**

The score is a summary. Check the evaluated periods; one score cannot establish full-session quality.

**Saved output**

QC is saved with the project. Logs and manual notes are under logs.

02 · Time start
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Start of the displayed recording window.

**Reference value:** 0 s

**Method considerations:** Inspect the beginning, middle, end, and intervals around key task events.

**Effect:** Changes the view and local metrics without cropping the source.

02 · Window
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Duration displayed at once.

**Reference value:** 60 ms

**Method considerations:** Use 20–100 ms for spikes and 1–10 s for slow artifacts or rhythms.

**Effect:** Short windows reveal waveforms; long windows reveal trends but compress spikes.

02 · Channel range
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** First channel and number shown together.

**Reference value:** Ch 0–11

**Method considerations:** Inspect 8–16 channels at a time on dense probes and move along depth.

**Effect:** Too many channels reduce readability; too few can hide spatially shared patterns.

02 · Display gain
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Vertical display multiplier only.

**Reference value:** 1.0×

**Method considerations:** Start at 1.0×, decrease for overlap, and increase for small traces.

**Effect:** Does not alter data or QC values; it only changes the view.

02 · Line frequency
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Center frequency for narrowband mains-power measurement.

**Reference value:** 50 Hz in China and most regions

**Method considerations:** Choose 50 or 60 Hz for the recording location and inspect harmonics.

**Effect:** The wrong choice misses mains noise but does not alter the source.

`Method documentation <https://spikeinterface.readthedocs.io/en/latest/modules/preprocessing.html>`__

Preview AP and LFP preprocessing
----------------------------------------------------------------------------------------------------

Compare a short segment before and after processing and inspect the recorded processing chain.

**Have ready**

Raw voltage and verified acquisition metadata. Complete Raw QC first.

1. **Generate the preview**

   Open Preprocessing and click Run selected analysis to generate a short-segment preview.

2. **Choose the signal branch**

   Switch between AP / sorting branch and LFP branch and compare traces and spectra.

3. **Check the processing chain**

   Open Auditable chain and safeguards. On the sorting page, also read the selected sorter's input contract and internal processing.

**Check the result**

This preview does not feed pre-whitened data to Kilosort4. The processing-chain record lists the preview parameters.

**Saved output**

Preview results and processing parameters are stored in the project for later inspection.

03 · AP band
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Passband used for spike detection or preview.

**Reference value:** 300–6000 Hz

**Method considerations:** Start with sorter/domain defaults and adjust only from sampling rate and spectral evidence.

**Effect:** A high lower cutoff suppresses broad spikes; a low one retains LFP drift. The upper cutoff must stay below Nyquist.

03 · LFP low-pass
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Highest retained LFP frequency.

**Reference value:** 300 Hz

**Method considerations:** Use 150–250 Hz for analyses below 100 Hz; retain a higher cutoff and sampling rate for high-frequency oscillations.

**Effect:** Lower cutoffs smooth transients; overly high cutoffs allow spike leakage into LFP.

03 · LFP sampling rate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Samples per second retained after LFP filtering.

**Reference value:** 1,000 Hz

**Method considerations:** Keep at least twice the highest target frequency; 4–10× margin is common.

**Effect:** Too low causes aliasing or poor phase precision; too high increases memory and computation.

03 · Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Common reference estimate subtracted from each channel.

**Reference value:** Common median

**Method considerations:** Start with median for dense recordings; use probe groups and reference design for sparse tetrodes or microwires.

**Effect:** Average is more sensitive to outliers; median is robust, but both can remove genuine common activity.

03 · Notch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Suppresses 50/60 Hz and optional harmonics.

**Reference value:** Off

**Method considerations:** Enable only when QC shows narrowband contamination that cannot be corrected at acquisition.

**Effect:** Notching changes amplitude and phase around the target and can affect coupling analyses.

`Method documentation <https://spikeinterface.readthedocs.io/en/latest/modules/preprocessing.html>`__

Select and run a sorter
----------------------------------------------------------------------------------------------------

Check the environment and probe requirements, then run a sorter and retain its output for comparison.

**Have ready**

Raw voltage, the correct rate and channel geometry, and an available sorter environment.

1. **Check availability**

   Open Spike sorting and inspect Environment, Hardware, and Best suited recordings. Use Edit → Sorter manager… if dependencies are missing.

2. **Select and verify parameters**

   Select the sorter row. Kilosort4 exposes presets, batch\_size, drift blocks, and thresholds; MountainSort5 exposes scheme, detection threshold, and training duration.

3. **Run and inspect diagnostics**

   Click the bottom Run button and verify the sorter in the confirmation dialog. After completion, use Post-run diagnostic view and continue to Unit QC.

**Check the result**

Simple is useful for quick workflow checks. Choose a method suited to the recording and curate its units for analysis.

**Saved output**

Native results and logs are under the sorter's folder in results. Normalized output is saved with the project.

04 · Sorter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Spike-sorting backend that will actually run.

**Reference value:** Kilosort4

**Method considerations:** Evaluate Kilosort4 first for dense Neuropixels; compare CPU sorters for sparse/tetrode recordings.

**Effect:** Sorters differ in preprocessing, detection, clustering, and resources; they are not interchangeable parameter presets.

04 · n\_chan\_bin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Total channels in the Kilosort binary, including channels not used for sorting.

**Reference value:** Read from the project structure

**Method considerations:** Must match the physical file layout; Neuropixels 1.0 files commonly contain 385 channels.

**Effect:** A wrong value creates diagonal/repeated heatmaps and should stop the run immediately.

04 · batch\_size
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Samples processed in each Kilosort batch.

**Reference value:** 60,000 (2 s at 30 kHz)

**Method considerations:** Start with the default; for ≤64 channels, a longer batch can improve drift estimation.

**Effect:** Larger batches need more memory; short batches contain fewer spikes for drift estimation.

04 · nblocks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Number of depth blocks used for drift correction.

**Reference value:** 1 (rigid drift)

**Method considerations:** Start at 1 for a single-shank Neuropixels probe, try 5 for non-rigid drift, and consider 0 for ≤64 sparse channels around ≥50 µm spacing.

**Effect:** Zero disables correction; too many blocks make sparse estimates unstable.

04 · Th\_universal / Th\_learned
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Detection thresholds for universal and learned templates.

**Reference value:** Current Kilosort4 default

**Method considerations:** Start with defaults; lower by only 1–2 at a time when spikes are missed or units disappear.

**Effect:** Lower thresholds detect more events but increase noise and computation.

04 · tmin / tmax
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Start and end times included in sorting.

**Reference value:** Full recording

**Method considerations:** Crop only confirmed start/end artifacts and document the exclusion.

**Effect:** Short ranges speed testing but cannot establish full-session stability.

04 · duplicate\_spike\_ms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Window for removing near-duplicate spikes within a unit.

**Reference value:** Kilosort4 default

**Method considerations:** Adjust only for a supported duplicate peak around zero in the ACG; never exceed 0.5 ms.

**Effect:** Large values corrupt refractory-period and ACG/CCG estimates.

`Method documentation <https://kilosort.readthedocs.io/en/latest/>`__

Review and label units
----------------------------------------------------------------------------------------------------

Review automated metrics alongside waveforms, ISIs, and stability, then save a curation decision.

**Have ready**

A completed or imported sorting result. Waveform diagnostics depend on available data.

1. **Calculate Unit metrics**

   Open Unit QC and run the stage. Use the title dropdown for Unit metric overview or one unit's waveform/ACG/ISI/stability.

2. **Open manual curation**

   Click Open manual Unit curation. Select a unit on the left, inspect the center plots, and set Decision, Confidence, and Reviewer on the right.

3. **Save the evidence**

   Check the evidence you reviewed, enter Notes, click Save decision, and move to the next unit.

**Check the result**

Labels and notes are saved. This workbench does not merge or split clusters; missing metrics are not passing evidence.

**Saved output**

Curation records are saved with the project and can be included in exported results.

05 · Firing rate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Spikes per second over valid recording time.

**Reference value:** Report only; no automatic exclusion

**Method considerations:** Interpret with brain region, cell type, duration, and stability.

**Effect:** A higher minimum removes sparse units but can discard real low-rate cells.

05 · ISI violation window
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Window used to count refractory-period violations.

**Reference value:** 2 ms

**Method considerations:** Start around 1–2 ms and report the exact definition.

**Effect:** Larger windows count more violations; values are incomparable without the definition.

05 · SNR
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Waveform signal magnitude relative to background noise.

**Reference value:** Report only

**Method considerations:** Use one method consistently and inspect waveforms; do not transfer thresholds blindly across tools.

**Effect:** Higher thresholds are conservative but penalize real low-amplitude units.

05 · Amplitude stability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Change in spike amplitude over time.

**Reference value:** Full-session timeline

**Method considerations:** Look for decay, jumps, or brief presence and compare with drift diagnostics.

**Effect:** Overly strict criteria reject real state changes; loose criteria retain drifting or disappearing units.

05 · Contamination threshold
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Allowed estimated contamination.

**Reference value:** Not treated as ground truth

**Method considerations:** If 10% is shown as a guide, report the estimator and review it with ACG and waveforms.

**Effect:** Lower thresholds reduce unit count and increase conservatism, but the estimate is itself uncertain.

`Method documentation <https://spikeinterface.readthedocs.io/en/latest/modules/qualitymetrics.html>`__

Align behavior to the recording
----------------------------------------------------------------------------------------------------

Import behavior and synchronization pulses, then verify timing before event-response analysis.

**Have ready**

A generic event CSV or MED-PC C/D arrays. A separate behavior clock also needs corresponding TTL pulses.

1. **Import behavior and TTLs**

   Open Event synchronization and click Import / replace behavior and TTL. Select the format and files; Open Ephys can supply recorded digital inputs.

2. **Check clock sources**

   Check CSV time units. For MED-PC, verify the behavior synchronization code and recorded TTL channel, then save and run this stage.

3. **Inspect alignment**

   Inspect pulse counts, matches, offset, drift, and residuals. Verify that events fall within the recording.

**Check the result**

Missing or duplicate pulses and an incorrect channel affect ordered pairing. Correct event inputs before interpreting neural responses.

**Saved output**

Import settings, alignment records, events, and defined trials are stored in the project.

06 · Behavior time column
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Column containing behavior-device timestamps.

**Reference value:** time\_seconds

**Method considerations:** Convert to seconds while retaining the source column; frame indices require frame rate or per-frame timestamps.

**Effect:** A unit mistake creates 1000× or sampling-rate-scale errors.

06 · TTL pairing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** How behavior and ephys pulses are paired.

**Reference value:** Pair one-to-one in order

**Method considerations:** Check counts and intervals first; locate missing pulses from interval patterns before pairing.

**Effect:** One missing pulse shifts all subsequent order-based pairs.

06 · Clock model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Function mapping behavior time to ephys time.

**Reference value:** offset + slope × time

**Method considerations:** Start linear; use segmented or nonlinear models only for curved residuals or clock jumps.

**Effect:** An overly complex model fits pulse jitter; an overly simple model leaves systematic drift.

06 · Residual tolerance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Maximum allowed timing error after alignment.

**Reference value:** Report the observed value without hiding it

**Method considerations:** Set from task timescale and device precision; millisecond spike responses require tighter limits.

**Effect:** Loose tolerance retains mismatches; strict tolerance rejects normal TTL jitter.

06 · Shared-clock assumption
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Whether behavior seconds are treated directly as ephys seconds without TTLs.

**Reference value:** Enabled with a warning only when TTLs are absent

**Method considerations:** Use only with a shared hardware clock or externally completed synchronization.

**Effect:** Cannot detect offset or drift; the limitation must appear in the report.

Inspect behavior and trials
----------------------------------------------------------------------------------------------------

Check behavioral completeness before choosing conditions for neural comparisons.

**Have ready**

Imported behavior events. Reaction time, choice, and psychometrics require their corresponding trial fields.

1. **Generate the summary**

   Open Behavior analysis and run this stage. Inspect event count, trial count, and the behavior plots.

2. **Check conditions and sample sizes**

   Review trial counts by condition and available reaction times and choices. Check the source behavior file when samples or fields are missing.

3. **Choose the neural analysis**

   After identifying the alignment event and conditions, continue to Neural activity.

**Check the result**

Event times alone do not supply choices, accuracy, or reaction times. Check source fields when a panel is empty.

**Saved output**

Behavior summaries are saved with the project; run Publication and reproducibility for related exports.

07 · Condition column
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Trial field used for group comparisons.

**Reference value:** condition

**Method considerations:** Use original task labels and maintain a data dictionary.

**Effect:** Recoding changes groups and counts; preserve the mapping.

07 · Reaction-time start/end
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Two events defining reaction time.

**Reference value:** stimulus\_onset → response

**Method considerations:** Define from the scientific question; movement onset, button press, and reward are not interchangeable.

**Effect:** Different endpoints change both values and neural interpretation.

07 · Minimum trials
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Minimum valid trials required for a condition.

**Reference value:** Warning only; no automatic exclusion

**Method considerations:** Use power analysis based on effect, variance, and validation design rather than one universal count.

**Effect:** Higher thresholds improve stability but exclude more sessions.

07 · Outlier rule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Rule defining outliers in reaction time or continuous behavior.

**Reference value:** No deletion by default

**Method considerations:** Prefer task-defined limits or robust rules and report excluded counts.

**Effect:** Post-hoc limits can change condition effects and introduce bias.

Choose a neural analysis
----------------------------------------------------------------------------------------------------

One page offers several analyses. Use the dropdown beside the title to choose the question for this run.

**Have ready**

Spike analysis needs units, event responses need event times, and LFP or spike-field analysis needs available voltage.

1. **Select the analysis**

   Choose Event · Unit … for a unit's event response; choose spike-train statistics or relationships for spike analyses. Population, fine timing, and LFP have separate entries.

2. **Run the selected analysis**

   Click Run selected analysis. Population dynamics and fine timing open settings dialogs; other choices use current project and method parameters.

3. **Inspect plots and tables**

   For event responses, inspect the raster and PSTH, alignment zero, and valid trial count. Switch views for related results and zoom with the plot toolbar.

**Check the result**

The dropdown selects analyses and result views. Check the bottom Current description after changing it before running.

**Saved output**

Completed analyses are retained in the project; export plots through Publication and reproducibility.

08 · Alignment event
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Time zero for every trial.

**Reference value:** stimulus\_onset (depends on the event table)

**Method considerations:** Choose from the hypothesis; stimulus, movement, choice, and reward answer different questions.

**Effect:** Changing the event changes temporal interpretation and must not be significance-driven.

08 · Window
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Time range extracted around the event.

**Reference value:** -1 to +2 s

**Method considerations:** Cover baseline and expected response while avoiding neighboring trials or events.

**Effect:** Short windows miss slow responses; long windows increase overlap and multiplicity.

08 · Bin size
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Temporal bin width for PSTH or count features.

**Reference value:** 50 ms

**Method considerations:** Use 5–20 ms for fast sensory responses and 20–100 ms for behavioral/population trends, with sensitivity checks.

**Effect:** Small bins improve resolution but are noisy; large bins smooth responses and lower peaks.

08 · Smoothing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Kernel and width applied to binned firing rates.

**Reference value:** Minimal or off

**Method considerations:** Smoothing is acceptable for display; statistics should prefer unsmoothed trial features and report the kernel.

**Effect:** Stronger smoothing lowers peaks, broadens responses, and induces temporal dependence.

08 · PSD method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Power-spectral estimator and segmentation settings.

**Reference value:** Welch

**Method considerations:** Start with Welch for stationary segments and report window, overlap, resolution, and units.

**Effect:** Long windows improve frequency resolution but reduce temporal localization, and vice versa.

08 · Surrogates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Number of time shifts or label shuffles used for a chance distribution.

**Reference value:** 200 (demonstration)

**Method considerations:** Use at least 1,000 for formal analysis and more for tail p-values; fix the random seed.

**Effect:** Fewer runs are faster but give coarse p-values; more runs are stable but expensive.

Inspect statistical evidence
----------------------------------------------------------------------------------------------------

Review condition differences, effect sizes, and sample structure together to assess the test's suitability.

**Have ready**

Completed neural analysis with comparable conditions or paired responses.

1. **Run the statistical suite**

   Open Statistical tests and click Run selected analysis.

2. **Inspect the design first**

   Choose Sampling hierarchy and test decisions. Check whether samples are trials, units, sessions, or animals and whether measurements are paired.

3. **Inspect effects and tests**

   Use Condition tests and effects and Effects and multiplicity to inspect effect direction, confidence intervals, and corrected values; inspect distribution or phase tests as needed.

**Check the result**

The dropdown switches result views; it is not an editor for every test parameter. Verify grouping for multi-animal or multi-session designs.

**Saved output**

Statistics are saved with the project; full export includes related tables and method records.

09 · Sampling unit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Independent observational unit used for inference.

**Reference value:** Must be confirmed by the user

**Method considerations:** Animal-level claims usually require animals as independent units, with units/sessions nested.

**Effect:** Too fine inflates n and significance; too coarse loses information.

09 · Paired
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Whether conditions come from the same or matched observational unit.

**Reference value:** Defined by the study design

**Method considerations:** Use paired tests for repeated observations from the same unit/session/animal.

**Effect:** Incorrect pairing changes the error term and statistical power.

09 · Alpha
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Predefined type-I error threshold.

**Reference value:** 0.05

**Method considerations:** Set before analysis and report together with multiplicity correction.

**Effect:** Lower alpha is conservative but increases misses; never change it post hoc for significance.

09 · Multiple comparison
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Method controlling error across a family of tests.

**Reference value:** FDR Benjamini–Hochberg

**Method considerations:** Use FDR for exploratory multi-unit/time tests and Holm for a few planned comparisons; define the family.

**Effect:** Stricter correction reduces false positives and power; correction is meaningless without a defined family.

09 · Resamples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Number of permutation or bootstrap repetitions.

**Reference value:** 1,000

**Method considerations:** Use 200–1,000 for preview and often 5,000–10,000 for final estimates with a fixed seed.

**Effect:** Controls Monte Carlo stability of p-values/intervals and runtime.

Run classification or regression
----------------------------------------------------------------------------------------------------

Test whether neural features predict a task variable and inspect cross-validation and baseline results.

**Have ready**

Valid trials, neural features, and classification labels or a continuous behavior target.

1. **Choose the task and model**

   Open Machine learning and select Classification · … or Regression · … beside the title. Classification predicts categories; regression predicts continuous values.

2. **Run the model**

   Click Run selected analysis and verify the model name in the confirmation dialog.

3. **Check validation results**

   For classification, inspect confusion, cross-validation, and permutation baseline; for regression, inspect predictions versus observations and errors. Compare models on the same data scope.

**Check the result**

Verify the actual features, sample count, and split strategy in the results. Neither a PCA plot nor a high score establishes causality.

**Saved output**

Model evaluations and parameters are saved with the project and exported through Publication and reproducibility.

10 · Feature window
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Time range used to extract neural features for each trial.

**Reference value:** 0–0.5 s (task-dependent)

**Method considerations:** Predefine from causal timing; do not use post-behavior information to predict behavior.

**Effect:** Long windows contain more information but can include later events and movement.

10 · Cross-validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Train/validation split and repetition scheme.

**Reference value:** 5-fold stratified or grouped

**Method considerations:** Use GroupKFold or LeaveOneGroupOut when sessions or animals must not cross folds.

**Effect:** Random trial splits often score higher but may learn session identity.

10 · Scaling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Feature standardization or normalization.

**Reference value:** StandardScaler for linear/SVM models

**Method considerations:** Fit within every training fold and apply to its validation fold.

**Effect:** Scaling the full dataset first leaks validation means and variances.

10 · Class weighting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Loss weights for imbalanced classes.

**Reference value:** balanced (for imbalanced classes)

**Method considerations:** Report class counts first; weighting or resampling must occur inside training folds.

**Effect:** Changes decision boundaries and calibration; ordinary accuracy is insufficient.

10 · Permutation count
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Number of label shuffles with complete re-validation.

**Reference value:** 200 (demonstration)

**Method considerations:** Use at least 1,000 for final results while preserving group structure.

**Effect:** One shuffle is unstable; invalid shuffling destroys nesting.

`Method documentation <https://scikit-learn.org/stable/common_pitfalls.html>`__

Save projects, figures, and records
----------------------------------------------------------------------------------------------------

Save to resume later; export figures, tables, and records for review, editing, and sharing.

**Have ready**

An open project with the analyses you want to export completed.

1. **Save the project**

   Press Ctrl+S or choose File → Save project. After saving, reopen the manifest to continue later.

2. **Prepare figures**

   Use Figure settings on analysis pages to adjust plots, or select and save an individual panel. For the full export, run Publication and reproducibility.

3. **Find outputs and logs**

   Choose File → Open project folder. Read the file beginning with 00\_README\_; exports holds figures and tables, results holds analysis output, and logs holds experiment logs and notes.

**Check the result**

Before delivery, inspect exported titles, axes, units, and statistical annotations. Back up external source data when the project depends on them.

**Saved output**

neuroflow\_project.json, inputs, config, logs, cache, derived, results, and exports form the project record.

11 · Format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Figure file type.

**Reference value:** PNG + SVG

**Method considerations:** Use PNG for preview and SVG/PDF for vector editing and publication.

**Effect:** Raster output depends on DPI; vector output preserves line and text objects.

11 · Figure size
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Output width and height.

**Reference value:** Use the current figure

**Method considerations:** Set journal single/double-column dimensions in millimeters and inspect long labels.

**Effect:** Changing dimensions alters relative text size and panel spacing.

11 · DPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Pixels per inch for raster output.

**Reference value:** 300

**Method considerations:** Use 300–600 DPI for line art and follow journal/source resolution for images or heatmaps.

**Effect:** Higher DPI increases file size but cannot add source-data resolution.

11 · Axis/grid/spine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Axis line width, extent, ticks, grid, and spine visibility.

**Reference value:** NeuroEphys AI standard theme

**Method considerations:** Adjust by plot type and keep a figure consistent; do not let decorative grids obscure data.

**Effect:** Thick lines improve visibility but crowd small panels; strong grids compete with data.

11 · Project source mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Meaning:** Whether the project uses an external read-only link or an internal raw copy.

**Reference value:** Defined by the import choice

**Method considerations:** Before archiving, verify external paths; copy raw data or use stable shared storage for portability.

**Effect:** The manifest remains readable, but raw-dependent stages cannot rerun if an external source is missing.
