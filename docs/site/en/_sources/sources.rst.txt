Methods, software, and sources
==============================

NeuroEphys AI calls established libraries through their public interfaces and
adds original project, adapter, workflow, explanation, figure, and audit
layers. The documentation summarizes methods in original wording.

Core sources
------------

* `SpikeInterface documentation <https://spikeinterface.readthedocs.io/en/stable/>`_
  — recording extractors, preprocessing, sorter interface, postprocessing, and
  quality metrics.
* `Kilosort4 documentation <https://kilosort.readthedocs.io/en/latest/>`_
  — installation, parameters, execution, exported files, and Phy integration.
* `Elephant documentation <https://elephant.readthedocs.io/en/latest/>`_
  — Neo-based spike-train and electrophysiology analyses.
* `Neo documentation <https://neo.readthedocs.io/en/stable/>`_
  — common electrophysiology data objects.
* `NWB documentation <https://nwb-overview.readthedocs.io/>`_
  — standardized neurophysiology data organization.
* `IBL ONE documentation <https://int-brain-lab.github.io/ONE/>`_
  — public IBL data access and ALF objects.
* `DANDI Archive documentation <https://docs.dandiarchive.org/>`_
  — public NWB dataset discovery and access.
* `Trautmann et al. 2025 <https://doi.org/10.1038/s41593-025-01976-5>`_ and
  `public Fig. 7 data/code <https://zenodo.org/records/7946011>`_
  — external NHP high-density-recording acceptance test and disclosed
  single-trial/fine-timing method definitions.
* `Rastermap paper and official code <https://github.com/MouseLand/rastermap>`_
  — optional population-ordering backend; built-in peak-time and PCA ordering
  remain available when it is not installed.
* `DeepSeek API documentation <https://api-docs.deepseek.com/>`_
  — optional online structured generation and tool-call transport.
* `Ollama OpenAI compatibility <https://docs.ollama.com/api/openai-compatibility>`_
  — optional local compatible model endpoint.

Attribution and data
--------------------

Every public validation project records its dataset identifier, version, source
URL, and local transformation. Private recordings are excluded from the public
repository and release archive. Third-party licenses remain with their
respective projects; this repository does not redistribute their source code or
documentation text.
