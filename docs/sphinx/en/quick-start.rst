First use: complete a small project
==================================================

Use the bundled 8-channel microwire teaching example to obtain a raw-QC result,
save one figure, and reopen the project. You do not need experimental data, an AI
provider, or a GPU for this exercise.

1. Open a teaching example
--------------------------------------------------

On the home screen select **Example projects**, choose the **8-channel microwire**
entry with type **Teaching**, then **Open selected example**. Teaching data are
generated locally. Public examples are separate entries and may require a download.

In **01 Data and project**, check the name, project location, channel count, and
duration. Raw traces should appear in the center. If they do not, inspect the status
bar and audit log before starting later analyses.

2. Run raw QC
-------------

Choose **02 Raw QC** in the workflow. Review the page's analysis selection and click
**Run selected analysis** in the bottom bar, or press **Ctrl+Enter**.

When the analysis finishes, change the diagnostic view to inspect noise, saturation,
or channel-quality summaries. Return to the trace view to check the evidence.
A QC score helps screen channels; use the traces and acquisition conditions when
deciding whether to exclude a channel.

.. tip::

   **Next step** changes the page; it does not run the calculation. If a page shows
   an old figure or a pending-analysis message, check the selected analysis in the
   bottom bar and its completion status.

3. Save one figure
------------------

Expand **Plot tools**, select a panel, and use **Expand selected panel**
to inspect axes and units. Use **Edit selected panel** if you need to adjust a title
or ticks, then **Save selected panel** as PNG or SVG. For this exercise, choose the
project's ``exports/figures`` directory.

Use **Show all panels** to return to the full figure. A style edit does not recalculate
statistics or change analysis settings.

4. Save and reopen
------------------

Press **Ctrl+S**. Use **File → Open project folder** and locate:

* ``neuroflow_project.json`` — the entry point for reopening your work;
* the file beginning with ``00_README_`` — the project and directory guide;
* the Markdown file in ``logs/`` — the human-readable run record, currently in Chinese;
* ``exports/figures`` — the figure you chose to save.

Choose **View → Back to home**, then **Open / import project** and select that
``neuroflow_project.json``. Return to raw QC and confirm the project name and saved
QC results are available.

The exercise is complete when you can locate the project, find the exported figure,
and reopen the previous result.

Continue with sorting
---------------------

Read :doc:`sorting-curation` next. In **04 Spike sorting**, choose a sorter whose
environment is available; a CPU method is a practical starting point for the
microwire example. Kilosort4 depends on the local installation and GPU status.
**Edit → Sorter manager** shows the actual detection results.

After sorting, use **05 Unit QC → Open manual unit curation workbench** to inspect
candidates. Known spike times in teaching data allow simulated validation; they do
not establish accuracy on real experimental data.

Continue to :doc:`events-analysis` for event figures, or :doc:`first-project` when
you are ready to use your own recording.
