Create and reopen a project
===========================

A NeuroEphys AI project stores links to source files, selected channels,
recording metadata, parameters, intermediate products, figures, decisions, and
audit records. Original voltage files remain read-only.

Create the project
------------------

1. Start the application and choose **Create empty project**.
2. Enter a project name and a writable project folder.
3. On **01 Data and project**, select **Import my data**.
4. Choose the route that describes the files you actually hold:

   * generic interleaved binary;
   * acquisition-system files;
   * an existing Kilosort/Phy result;
   * an Offline Sorter/NeuroExplorer ``.nex5`` result;
   * a verified public-data project;
   * a teaching simulation.

5. Review the recognition preview before creating the data link. Confirm
   sampling rate, channel count, numeric type, voltage scale, recording
   duration, selected contacts, and event source.

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
**Restore NeuroEphys AI project** on the home screen to reopen the manifest.

After recovery, check that the source link is reachable. Derived results remain
visible when possible; stages that require a missing external file are disabled
with a specific message.

Visible changes after import
----------------------------

The Data and project page updates its source type, channel count, duration,
signal unit, probe metadata, behavior inventory, and workflow starting point.
The right-side audit panel records the input and generated project paths.
