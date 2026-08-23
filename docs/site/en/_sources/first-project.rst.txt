Create and reopen a project
===========================

A NeuroEphys AI project stores links to source files, selected channels,
recording metadata, parameters, intermediate products, figures, decisions, and
audit records. Original voltage files remain read-only.

Create the project
------------------

1. Start the application and choose **New project**.
2. Enter a project name and choose the route that describes the files you
   actually hold:

   * generic interleaved binary;
   * acquisition-system files;
   * an existing Kilosort/Phy result;
   * an Offline Sorter/NeuroExplorer ``.nex5`` result;

3. Review the recognition preview before creating the data link. Confirm
   sampling rate, channel count, numeric type, voltage scale, recording
   duration, selected contacts, and event source.

Use **Open / import project** for a previously saved
``neuroflow_project.json``. **Example projects** combines teaching simulations
and fixed verified public projects. The home screen no longer repeats the full
input-route table; detailed format choices appear only while creating a project.

Layout and beginner guidance
----------------------------

The workspace shows three columns together by default: workflow navigation on
the left, the analysis canvas in the center, and AI/help/audit on the right.
Drag the dividers to resize them. The left control compacts the workflow into a
narrow ``01``–``11`` rail, while the right close control temporarily hides the
AI column. In a narrow window the workflow rail compacts automatically and the
center retains scroll access instead of clipping wide controls or figures.

A short step guide appears on the first visit to each stage. It explains the
stage purpose, recommended order, and completion checks. Select **Do not show
step guides automatically** to disable the prompts. Re-enable or reset them from
the **Help** menu.

Acquisition metadata
--------------------

Record the electrode type, brain region, contact organization, reference
method, online acquisition filters, and known bad channels. These fields affect
later safeguards. For example, an acquisition already high-pass filtered at
250 Hz cannot support an authentic LFP branch.

Save and recover
----------------

Use **Save project** after changing inputs, curation labels, analysis settings,
or figure styles. Closing a modified project opens a save prompt. Choose
**Open / import project** on the home screen to reopen the manifest.

After recovery, check that the source link is reachable. Derived results remain
visible when possible; stages that require a missing external file are disabled
with a specific message.

Visible changes after import
----------------------------

The Data and project page updates its source type, channel count, duration,
signal unit, probe metadata, behavior inventory, and workflow starting point.
The right-side audit panel records the input and generated project paths.
