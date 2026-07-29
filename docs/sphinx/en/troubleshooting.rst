Troubleshooting
===============

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
