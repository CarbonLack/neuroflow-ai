# Architecture

NeuroFlow separates five responsibilities:

1. **Project model** stores source provenance, parameters, results, and status.
2. **Import adapters** translate device formats and processed ALF/Phy results.
3. **Workflow nodes** perform deterministic QC, sorting, analysis, and export.
4. **Tutorial and rule layer** explains decisions without hiding parameters.
5. **Optional assistant layer** may later propose workflows but is not required.

Raw source files are treated as read-only. Device adapters use SpikeInterface
extractors and cache a normalized project-local binary. Processed ALF or
Kilosort outputs may enter after the raw/sorting stages, and unavailable nodes
are explicitly marked as skipped rather than faked.

Sorter adapters are capability-checked. Kilosort4 has a native NeuroFlow
adapter. MountainSort5, SpyKING CIRCUS 2, and Tridesclous 2 use
SpikeInterface when their dependencies are actually installed. The UI never
labels an unavailable sorter as executable.
