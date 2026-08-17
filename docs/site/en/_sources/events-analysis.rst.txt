Behavior synchronization and event-aligned analysis
====================================================

Behavior and electrophysiology devices usually start at different times and
may drift. A shared TTL sequence provides anchors for mapping both clocks.

Import and map events
---------------------

On **06 Event synchronization**, import the behavior file, select the parser,
map numeric codes to event names, choose the electrophysiology digital-input
channel, and specify synchronization-on/off codes. Preview counts before
alignment. Task events and synchronization events are plotted separately by
default.

Alignment quality
-----------------

Check matched anchor count, unmatched pulses, residual distribution, residual
trend over time, and the fitted clock transformation. A small average residual
does not compensate for a missing block or a nonlinear timing error.

Raster and PSTH
---------------

Choose event codes or named conditions, an alignment window, bin size, baseline
window, and response window. The software filters events independently for
each condition and records the retained count.

The raster contains one row per retained event. Colored ticks identify
condition membership. The PSTH shows condition mean and standard error;
shaded regions mark the exact baseline and response windows. The population
heatmap uses baseline z-scores and a diverging color scale.

Single-trial and population dynamics
------------------------------------

Population-dynamics views on **08 Neural activity** open a settings review
before execution. Choose the event condition, brain-region unit scope, analysis
window, bin width, Gaussian smoothing :math:`\sigma`, baseline handling, and
unit ordering. Baselines can be pooled per unit across trials or estimated
separately for each trial. Ordering can use peak time, a PCA loading, or the
optional Rastermap backend. The same auditable result drives the ordered
heatmap, single-trial, condition-comparison, and PCA-trajectory views.

For variable-reaction-time tasks, the Python API also accepts an explicit valid
start/stop window for every trial so time outside a trial is not treated as zero
firing. Continuous-behavior regression keeps entire trials together during
train/test splitting and exposes neural-to-target lag and repeated neuron-count
scaling.

Fine-timing relationships
-------------------------

The fine-timing module does not label functional evidence as anatomical
connectivity. Choose count, reference-rate, or trial/rate/lag-edge-normalized
CCGs; fixed-interval or centered jitter; flank-SD or empirical-p inference;
FDR, Bonferroni, or no multiplicity correction; and within-region,
between-region, or spatial-distance filters. The run dialog estimates eligible
pairs and surrogate CCG workload before analysis starts.

Quality checks
--------------

* Verify event code semantics before interpreting left/right or success/failure
  curves.
* Confirm both condition counts and exclusion reasons.
* Inspect individual units before relying on a population average.
* Confirm the baseline lies outside the response period.
* Review FDR input and correction family when many units or bins are tested.

The event index is an ordering of retained events. It is labelled as a trial
only when a valid trial table defines that relationship.

.. raw:: html

   <img class="product-shot" src="../assets/neuroephys-event-analysis-en.png"
        alt="NeuroEphys AI event-aligned raster and PSTH workspace">

Scroll within the central workspace to inspect the population heatmap and
per-unit effect panel. Each panel can be expanded, edited, or exported
independently.

.. raw:: html

   <img class="product-shot" src="../assets/neuroephys-event-analysis-detail-en.png"
        alt="NeuroEphys AI population heatmap and unit effect detail">
