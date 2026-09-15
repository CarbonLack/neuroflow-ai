Figure inspection and publication export
========================================

Every scientific page exposes the current figure as an interactive Matplotlib
canvas. Use the toolbar to reset, move, zoom, inspect points, and save. Select a
panel to enlarge, edit, or export it without cropping a screenshot. Expand
**Plot tools** above the figure to reveal style, panel selection, and export controls.

Figure Studio
-------------

Panels are named from their actual titles, not ambiguous “Axis 1 / Axis 2” labels.
The object editor uses category tabs and paired controls; its preview follows the selected panel.
In **Shared style**, choose a preset and apply it to the **selected panel**, **whole figure**,
or **all project figures**. Save the project with Ctrl+S to retain shared-style overrides.
Applying to all project figures clears local shared-style overrides. Existing exports are not overwritten.
Fine-grained object edits affect the current canvas and must be exported separately.

Research defaults are Arial, 8 pt labels/ticks/legend, 9 pt titles, 0.75 pt axes, 0.8 pt data lines,
outward 3 pt ticks, no grid, no top/right frame, muted purple/green category colours and 600 DPI raster output.
A higher-contrast category palette and the original category colours remain selectable.
Data, units, limits, scales and heatmap normalization are preserved. Nature reference uses 7 pt:
there is no single universal journal specification. See
`official sources and design choices <https://github.com/CarbonLack/neuroflow-ai/blob/main/docs/FIGURE_STYLE_STANDARD_ZH.md>`_.

Open **Figure settings** for whole-figure controls or **Edit panel** for the
selected axis. The editor exposes:

* canvas size and export DPI;
* subplot position and physical axis size;
* titles, axis labels, limits, scales, and tick formatting;
* spine visibility, line width, color, and offset;
* major/minor tick intervals and grid styles;
* line color, width, style, marker, and transparency;
* scatter size, face/edge color, and transparency;
* bars, filled intervals, heatmaps, text, legends, and reference lines.

Export choices
--------------

* SVG for editable vector artwork.
* PDF for vector publication and review.
* PNG for presentation or submission previews.
* CSV/source tables for numerical traceability.

Publication checks
------------------

Run the final export step and open ``exports/publication/index.html`` in the project.
Main figures follow behavioral context, neural response and statistical evidence; remaining
figures and tables remain indexed as supplementary evidence without significance-based selection.
``figure_legends.md`` provides draft English legends and ``artifact_inventory.json`` records
file checksums. Figures are exported in English without changing the App language.

Researchers must review interpretations and target-journal requirements. The report is a draft,
not automatic journal certification. Do not conflate Wilcoxon tests in the event overview with
permutation tests in the statistical suite.

Confirm units, condition counts, normalization, baseline, uncertainty
definition, statistical marks, and color accessibility before export. Vector
editing after export must not alter the underlying values or remove required
method information.

.. raw:: html

   <img class="product-shot" src="../assets/neuroflow-figure-studio.png"
        alt="NeuroEphys AI Figure Studio">
