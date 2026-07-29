Real-data validation
====================

This chapter reports the engineering validation scope, parameters, and
scientific limits. Authorized raw recordings, identity information,
laboratory paths, and per-animal results remain local and are not distributed
with the repository or desktop package.

Validation questions
--------------------

The validation checks whether NeuroEphys AI can:

* import Open Ephys Legacy recordings directly from the graphical interface;
* preserve the selected channels, time range, acquisition settings, and
  electrode description in a project;
* read long recordings in bounded chunks;
* preserve native sorter output while normalizing common spike records to
  seconds;
* align MED-PC events with digital-input synchronization pulses;
* save, close, reopen, and continue a project;
* trace every figure, table, statistic, model result, and log entry to its
  inputs and parameters.

Data and acquisition limits
---------------------------

The authorized dataset was recorded with 32 independently arranged custom
microwires and Open Ephys Legacy. Rapid regression tests used at least 1,800 s
per recording; the long-recording regression covered 7,497.489 s.

The acquisition system had already applied a 250--8,000 Hz online filter and
reference. Genuine low-frequency content cannot be recovered. The project
therefore blocks LFP, low-frequency spectra, LFP coherence, and spike-field
coupling. High-frequency AP-band data are not presented as LFP.

Sorter cross-check
------------------

The same 30-minute segment was processed through several sorting routes:

.. list-table::
   :header-rows: 1
   :widths: 30 18 22 30

   * - Sorter
     - Candidate units
     - Spikes
     - Validation purpose
   * - Kilosort4, default
     - 4
     - 395,007
     - GPU reference route
   * - Kilosort4, sensitivity profile
     - 5
     - 1,176,945
     - threshold sensitivity
   * - MountainSort5
     - 89
     - 325,982
     - CPU route and algorithm contrast
   * - SpyKING CIRCUS 2
     - 1
     - 49,442
     - SpikeInterface adapter
   * - Tridesclous 2
     - 18
     - 196,250
     - SpikeInterface adapter

The recovered long-recording Kilosort4 result contains 12 candidate units and
2,195,626 spikes. These are algorithmic candidates, not manually certified
single neurons. Curation still requires waveform shape, refractory-period
evidence, amplitude stability, drift, duplicate risk, and split/merge review.
Different candidate counts expose threshold and algorithm effects; they do
not establish which sorter is more accurate.

External Offline Sorter results
-------------------------------

Two provider-supplied ``.nex5`` files were imported read-only through the
official ``nex5file`` Python API. A filename filter restricted the import to
the same ``SW#1`` recording. The LO file contained five candidate units and
the MO file contained three, for eight candidate units and 273,358 spikes in
total. External names, channel numbers, LO/MO groups, waveform summaries, and
source-file records were preserved while the common interface was normalized
to seconds plus unit identifiers.

The NEX5 document ended at 7,653.4056 s and the raw project at 7,497.4891 s.
The complete-recording route inferred a 155.9165 s end-alignment offset and
recorded that inference in provenance. It is not a substitute for an
independent synchronization signal. Segment projects reject automatic
end-alignment and require a manual or sync-derived offset.

The full-recording comparison matched eight external candidates against
twelve Kilosort4 candidates with a 0.5 ms tolerance and a ±2 ms lag search.
Only one assigned pair reached strong agreement. Several external units showed
high recall but low precision against a high-rate Kilosort cluster, consistent
with merging, contamination, or different unit definitions. The comparison
prioritizes manual curation; the external result is not ground truth and does
not establish whether the true neuron count is eight or twelve.

Behavior and synchronization
----------------------------

The 30-minute project contains 4,654 MED-PC events and 744 matched
synchronization-anchor pairs. Events are stored as ``event code + event name +
seconds``. Synchronization pulses are displayed separately by default so that
they do not obscure task-event counts.

No general trial definition has yet been configured for this experiment.
NeuroEphys AI therefore exports ``events.csv`` and does not mislabel individual
events as trials. A two-condition analysis records the two event codes,
included counts, time window, baseline, per-unit matrix shape, and statistical
source independently.

Statistical and decoding limits
-------------------------------

An early technical regression treated event codes 21 and 22 as left/right
conditions. Each contained 67 records, but all 67 timestamp pairs were
identical. The condition audit therefore rejected the 134 records as a valid
binary task. Its balanced accuracy of 0.425 and label-permutation ``p=0.961``
remain in the Bug history and are not reported as a valid condition result.

The corrected 30-minute regression used action-start codes 17 and 19, with 34
events per class and 68 events in total. The current project produced balanced
accuracy 0.7660, ROC AUC 0.803, and ``p=0.0196078`` from 50 label
permutations. Although the event definitions no longer overlap, this remains a
single-session software-path test with four candidate units and a low
permutation count. It cannot support a neural-encoding claim.

The long-recording regression produced balanced accuracy 0.8257 and
``p=0.0196078``. This remains a software regression result: the event
definition, permutation count, hierarchical sampling, and cross-animal
replication are not sufficient for a scientific encoding claim. The report
keeps that limitation visible.

Project recovery and provenance
-------------------------------

Save/reopen tests recover:

* the read-only raw-data link, channel selection, and analysis range;
* electrode, region, reference, online-filter, and LFP-block status;
* QC, sorting, unit metrics, and manual-curation structures;
* behavior mapping, synchronization, statistics, decoding, and figure style;
* structured run logs, artifact manifests, and project-local AI history.

Every run records stage, input, parameters, tool version, start/end time,
outputs, warnings, errors, and recovery advice. Full authorized paths and the
step-by-step runbook remain in the local project's ``exports/documentation``
directory. The public manual contains only de-identified engineering evidence.

Validation labels
-----------------

The interface and documentation distinguish:

* **validated with real data**;
* **validated with simulated data**;
* **interface implemented, not yet validated**.

Future public releases will add redistributable IBL and DANDI examples.
Public-dataset outputs validate the import and analysis path; they are not
presented as reproductions of the source paper.
