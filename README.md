# NeuroFlow AI Demo

This Windows desktop demo runs a complete extracellular electrophysiology path:

1. deterministic simulated multichannel raw voltage
2. raw signal quality control
3. preprocessing preview and parameter confirmation
4. real Kilosort4 spike sorting
5. unit quality metrics
6. event synchronization
7. Raster, PSTH, population response and statistics
8. figure, Methods and provenance export

The simulated recording contains known ground-truth units so the Kilosort result
can be evaluated rather than merely displayed.

## Run

Double-click `run_demo.bat`, or use:

```powershell
..\work\.venv312\Scripts\python.exe app.py
```

Kilosort4 requires PyTorch. GPU execution is selected when CUDA is available.

## Repository policy

The repository contains source code, tests, documentation, small configuration
files, and reproducible environment definitions. It does not contain raw
recordings, generated demo data, virtual environments, API keys, or temporary
Kilosort outputs.

Development is committed by verified milestone:

1. Commit a coherent change only after its focused tests pass.
2. Push stable checkpoints that another machine can install and run.
3. Tag demo releases after the complete workflow has been manually verified.
