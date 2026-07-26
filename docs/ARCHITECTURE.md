# Architecture

NeuroFlow separates five responsibilities:

1. **Project model** stores source provenance, parameters, results, and status.
2. **Import adapters** translate device formats and processed ALF/Phy results.
3. **Workflow nodes** perform deterministic QC, sorting, analysis, and export.
4. **Tutorial and rule layer** explains decisions without hiding parameters.
5. **Optional assistant layer** explains, reviews, and proposes workflows but is
   not required for any analysis.

Raw source files are treated as read-only. Device adapters use SpikeInterface
extractors and cache a normalized project-local binary. Processed ALF or
Kilosort outputs may enter after the raw/sorting stages, and unavailable nodes
are explicitly marked as skipped rather than faked.

Sorter adapters are capability-checked. Kilosort4 has a native NeuroFlow
adapter. MountainSort5, SpyKING CIRCUS 2, and Tridesclous 2 use
SpikeInterface when their dependencies are actually installed. The UI never
labels an unavailable sorter as executable.

Successful runs enter a multi-result registry rather than replacing the previous
sorter output. Each result keeps native files and a normalized, seconds-based
Unit/spike view. Any saved result can be activated for downstream stages.
SpikeInterface comparison then provides ground-truth benchmarking, symmetric
two-sorter matching, and multi-sorter consensus without confusing agreement with
accuracy.

The optional assistant sends only a compact, path-free project summary to a
configured cloud endpoint. Raw voltage, local paths, project identity, and API
keys never enter the model input. The Responses API provider requests strict
structured output and disables server-side response storage. A generic
OpenAI-compatible Chat provider is available for private or third-party
endpoints.

AI plans can contain only the 11 registered workflow stages. They are validated
again locally, saved as `advisory_not_executed`, and require user confirmation
before entering the project. Applying a plan never invokes a workflow node.
Actual computation remains behind the fixed run controls and their separate
confirmation dialog.
