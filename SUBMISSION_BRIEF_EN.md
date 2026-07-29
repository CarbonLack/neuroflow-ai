# NeuroEphys AI project brief

## AI application

NeuroEphys AI is a local-first desktop workspace for offline analysis of in
vivo multichannel extracellular electrophysiology. Projects can begin with
acquisition-system files, generic binary recordings, NWB, or existing sorting
output, then proceed through raw QC, acquisition-aware preprocessing, spike
sorting, manual Unit curation, behavioral synchronization, event analysis,
statistics, machine learning, editable figures, and reproducible export.

The controlled assistant reads structured summaries produced by local modules.
It explains data and parameters, detects missing prerequisites, proposes an
editable workflow, compares sorters, interprets anonymized errors, and may
propose allow-listed tools in collaborative mode. Deterministic modules perform
the computation. Online transfer, long tasks, and result replacement require
confirmation.

## Current pain points

An electrophysiology workflow crosses acquisition formats, Python
environments, GPU/CUDA stacks, sorters, behavioral clocks, statistical methods,
and figure software. Mature open-source tools provide many algorithms, yet
users still face incompatible inputs and outputs, dependency conflicts,
separate tutorials, poorly indexed intermediate products, missing records of
manual decisions, and unclear parameter consequences. Large unpublished
recordings are also a poor fit for mandatory cloud upload.

## Relationship to open-source projects

Kilosort4 supplies high-performance spike sorting. SpikeInterface supplies
recording, preprocessing, sorter, and quality-metric interfaces. Neo and
Elephant supply unit-aware data objects and spike-train/signal analysis. NWB
supplies a standard exchange format. NeuroEphys AI calls their public APIs,
records versions, and preserves native output.

The project contributes the desktop workspace, project manifest, normalized
seconds-based sorting interface, acquisition and behavior adapters, modular
workflow, acquisition safeguards, manual curation, Figure Studio, bilingual
parameter-level manual, structured audit trail, and controlled AI Provider and
confirmation layer. Sources and scopes are listed in
`THIRD_PARTY_SOURCES.md`; external product text, screenshots, interfaces, and
implementation code are not copied.

## AI providers and data safety

The first online profile uses DeepSeek. OpenAI-compatible, laboratory-private,
and Ollama providers are also represented by the same configurable interface.
Responses pass JSON Schema, allow-list, prerequisite, and parameter checks.
Manual analysis remains available when AI is disabled or offline.

Raw voltage, video, and complete behavior files stay local by default. Online
requests contain only user-previewed minimal summaries. Local paths, identity
fields, arrays, and API keys are removed. Credentials stay in process memory,
environment variables, or the operating-system vault, never in projects,
logs, reports, or Git.

## Expected gains and roles

The product targets less environment setup, format conversion, repeated
parameter entry, and manual Methods preparation, with stronger error
detection, handover, review, and reproducibility. Measured gains will be
reported from controlled user testing rather than estimated in advance.

Responsibilities cover product/scientific ownership, data validation, workflow
engineering, AI and security, and bilingual interaction/documentation. Actual
team member names should be assigned to these roles in the submission.
