NeuroEphys AI user manual
==================================================

.. raw:: html

   <p class="manual-kicker">Local electrophysiology workbench · v1.2.0</p>

Work from the files you have: inspect raw recordings, sort spikes, review units,
align events, and export results. These guides follow the application's controls.
For a first visit, use a teaching example to run QC, save a figure, and reopen the project.

.. raw:: html

   <nav class="task-links" aria-label="Start with your task">
     <a class="task-link" href="quick-start.html"><strong>Try your first project</strong><span>Open the 8-channel example, run QC, save a figure, and reopen your work.</span></a>
     <a class="task-link" href="first-project.html"><strong>Use your own data</strong><span>Choose an entry for raw recordings, existing sorting, or a saved project.</span></a>
     <a class="task-link" href="workspace.html"><strong>Find a control</strong><span>Adjust three columns, select an analysis, use help, and find shortcuts.</span></a>
     <a class="task-link" href="troubleshooting.html"><strong>Resolve a problem</strong><span>Check unavailable analyses, incorrect inputs, missing plots, and moved files.</span></a>
   </nav>

.. raw:: html

   <a href="../assets/neuroephys-workspace-zh.png"><img class="product-shot" src="../assets/neuroephys-workspace-zh.png" alt="NeuroEphys AI workspace with workflow navigation, analysis, and assistance"></a>
   <p class="figure-note">Click the screenshot to inspect it at full size. This overview uses the Chinese UI; control names below use the English UI.</p>

Choose a route
--------------

**Raw voltage available:** import and inspect the recording before choosing
preprocessing and a sorter. Review candidate units before downstream analyses.

**Kilosort, Phy, or manually sorted output available:** import the result, check
units and time conversion, and continue from unit QC. Sorting output alone cannot
replace raw voltage for rerunning sorting or recovering missing waveforms.

**Saved NeuroEphys AI project available:** choose **Open / import project** and
select ``neuroflow_project.json``. Keep the project folder and its linked source recording.

The eleven stages describe the workflow. Available analyses depend on the project's
inputs: event analyses need events; LFP analyses need preserved low frequencies.
Check the selected analysis in the bottom run bar before starting it.

.. toctree::
   :maxdepth: 1
   :caption: Start and work with projects

   quick-start
   requirements-install
   first-project
   workspace
   task-guide
   workflow
   provenance

.. toctree::
   :maxdepth: 1
   :caption: Find an analysis guide

   sorting-curation
   events-analysis
   statistics-ml
   figures
   ai-assistant

.. toctree::
   :maxdepth: 1
   :caption: Parameters, validation, and support

   parameter-reference
   real-data-validation
   troubleshooting
   sources

The Windows application and Python package share analysis capabilities; some script
options do not have an application control. See :doc:`real-data-validation` for the
tested scope of each module. Review candidate units and interpretations in the context
of the experiment.

`Chinese manual <../zh/index.html>`_ · `Download releases <https://github.com/CarbonLack/neuroflow-ai/releases>`_
