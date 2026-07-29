NeuroEphys AI
==============

**Development preview · v0.10.0-dev**

NeuroEphys AI is a local-first workbench for extracellular multichannel
electrophysiology. It keeps raw-data import, quality control, preprocessing,
spike sorting, manual unit curation, behavioral synchronization, neural
analysis, statistics, decoding, figure editing, and provenance in one
recoverable project.

The current release is a research prototype. Use it to inspect workflows,
evaluate interoperability, and provide reproducible feedback. Every candidate
unit and statistical result still requires scientific review.

.. raw:: html

   <img class="product-shot" src="../assets/neuroflow-analysis.png"
        alt="NeuroEphys AI analysis workspace">

What is currently working
-------------------------

* Teaching simulations for Neuropixels-like probes, tetrodes, and independent
  microwires, including behavior, TTL, and known spike times.
* Direct import routes for generic binary and supported acquisition systems.
* Replaceable sorter outputs normalized to seconds-based unit/spike records.
* Manual unit review with waveform, refractory-period, amplitude, and stability
  evidence.
* Event-aligned raster, PSTH, population heatmaps, statistics, decoding, and
  editable vector-figure export.
* Optional controlled AI assistance. Manual analysis remains available when no
  model service is configured.

Language
--------

`Chinese documentation <../zh/index.html>`_ · English documentation

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   requirements-install
   first-project
   workflow

.. toctree::
   :maxdepth: 2
   :caption: Scientific workflow

   sorting-curation
   events-analysis
   statistics-ml

.. toctree::
   :maxdepth: 2
   :caption: Product guide

   ai-assistant
   figures
   parameter-reference
   provenance
   real-data-validation
   troubleshooting
   sources
