Troubleshooting
===============

Missing figure controls or a cramped window
----------------------------------------------------

Expand **Plot tools** above the figure for panel selection, editing, and export.
Drag the dividers to resize the three columns. **Ctrl+B** collapses the workflow
labels; **Ctrl+J** shows or hides the assistant. Scroll long central content;
the bottom run bar remains available. **View → Reset workspace layout** restores
the layout without changing analysis results.

Small help text or repeated walkthrough prompts
----------------------------------------------------

Use **A+** in the Tutorial center to enlarge the body text; the size is remembered.
For an empty search, clear the query and reset the category to all tasks.
Turn off automatic prompts at the bottom of a step guide. You can still open
**Help → Tutorial center** or the current **Step guide** whenever needed.

A recent project is disabled or a recording is missing
------------------------------------------------------------

Recent projects store the manifest location. If you moved a folder, use
**Open / import project** to choose its ``neuroflow_project.json`` again.
Saving a project does not copy every external recording. Restore missing source
files to their original location, or import into a new project. Keep the old
project and its completed results.

Application does not start
--------------------------

Open the newest application log and read the first exception. Packaged builds
must include scientific-library metadata files and Matplotlib SVG support.
Report the executable version, Windows version, and first error line.

Sorter appears unavailable
--------------------------

Open **Sorter manager** and refresh. Check the selected backend version,
NVIDIA driver/GPU requirement, writable output folder, free disk space, and
the backend's native probe. A different sorter's availability does not imply
that the selected sorter ran.

PSTH conditions look identical
------------------------------

Verify the two event codes, retained counts, condition labels, per-event spike
arrays, baseline/response windows, and the selected unit. Similar curves may be
real; a review must demonstrate that the two filters were evaluated
independently.

LFP controls are disabled
-------------------------

Inspect acquisition metadata. A recording stored after an online 250 Hz
high-pass filter lacks the original low-frequency signal. NeuroEphys AI blocks
LFP spectrum and spike-field coupling in this case.

AI service fails
----------------

Check provider endpoint, model name, credential, network, quota, timeout, and
response format. The failed request leaves the project and manual analysis
controls intact. The error log excludes the secret and raw data.

Useful issue report
-------------------

Include the application version, redacted project manifest, current stage and
parameters, first error line, audit tail, sorter/backend version, hardware
status, and whether the teaching simulation reproduces the problem.
