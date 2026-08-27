Spike sorting and manual unit curation
======================================

Sorting assigns extracellular spike events to candidate units. Different
sorters can disagree because they use different detection, drift, clustering,
template, and deconvolution strategies. NeuroEphys AI therefore preserves
native results and converts only the common downstream fields.

Common result interface
-----------------------

Every imported result provides:

* unit identifier;
* spike times in seconds;
* source recording and sorter;
* sampling rate and conversion provenance;
* native output location;
* available templates, channels, amplitudes, and quality fields.

Sorter-specific files remain untouched. Comparison views report matched,
split, merged, unique, and consensus candidates. Agreement between two sorter
outputs on real data is not ground-truth accuracy.

Using the side-by-side comparison
---------------------------------

1. Save at least two sorting results from the same recording and time window.
2. On stage 04, select **Normalized sorter comparison** as the post-run view.
3. Select a pair in **Side-by-side sorting comparison**. The two columns show
   Units, spikes, unique Units, backend, and version.
4. Inspect mean matched agreement and the Unit agreement matrix. CSV and full
   JSON exports are saved under ``results/sorting_comparison/``.

The calculation uses SpikeInterface ``compare_two_sorters`` and
``compare_multiple_sorters``. A symmetric pair comparison treats neither result
as truth, and a consensus can inherit weaknesses from its component algorithms.
See the official `SpikeInterface comparison module
<https://spikeinterface.readthedocs.io/en/latest/modules/comparison.html>`_.

Kilosort4 workflow
------------------

1. Select **Kilosort4** in the sorting workbench.
2. Confirm the probe/contact model and data type.
3. Inspect exposed parameters and the GPU/environment status.
4. Run the selected node and retain the native log.
5. Inspect depth-time activity, amplitudes, templates, template similarity,
   contamination estimates, and exported arrays.
6. Continue to Unit QC before event-aligned interpretation.

Manual curation
---------------

Manual review is expected for all sorters. The relative importance of each
diagnostic varies with the probe and recording, but the decision itself must be
recorded.

* A clear, stable waveform supports a candidate; waveform shape alone cannot
  prove cell identity.
* Refractory-period violations indicate contamination, merging, duplicate
  detection, or biological/threshold complications.
* Amplitude loss or movement across contacts can indicate drift or incomplete
  detection.
* Similar templates and near-synchronous spikes across units may indicate
  duplicate or split units.
* Low-rate units need enough spikes for a meaningful quality estimate.

Keep single units, multi-unit activity, and uncertain candidates as separate
labels. Downstream analyses can select the desired class without deleting the
original sorter output.
