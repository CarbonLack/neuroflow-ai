# NeuroEphys AI installation and complete user guide

> This is the user-facing GitHub entry point. Raw recordings stay local by default. Candidate clusters, automated screening, statistical significance, and AI suggestions all require researcher review.

## 1. Choose an edition

Download from [GitHub Releases](https://github.com/CarbonLack/neuroflow-ai/releases/latest).

| Edition | Recommended for | How to start | Important note |
|---|---|---|---|
| **Full offline installer (recommended)** `NeuroEphysAI-Setup-1.3.1-Full.exe` | Competition demos, research workstations, Kilosort/GPU use | Run the installer and choose components | GPU availability still depends on compatible NVIDIA hardware and drivers |
| **Standard installer** `NeuroEphysAI-Setup-1.3.1.exe` | General Windows, teaching, CPU workflows | Run the installer | Optional sorter components can be added later |
| **Standard portable ZIP** `NeuroEphysAI-1.3.1-Windows-x64-portable.zip` | Computers without install permission | Extract everything, then run `NeuroEphysAI\NeuroEphysAI.exe` | Do not copy only the EXE |
| **Python wheel** `neuroephys_ai-1.3.1-py3-none-any.whl` | Scripts, batch processing, and API users | Install with `python -m pip` | Python 3.12 is recommended |

The Full portable ZIP is larger than GitHub's 2 GiB per-file limit, so GitHub primarily distributes the Full installer.

## 2. Install on Windows

1. Download an installer from the release page.
2. Optionally verify it against `SHA256SUMS.txt`.
3. Run the installer. The Full edition exposes selectable desktop, scientific-analysis, and GPU/Kilosort components.
4. Start **NeuroEphys AI** from the shortcut.
5. Open **Help > Environment check** and review available sorters, compute support, and disk space.

The default workspace is `Documents\NeuroEphysAI`. Source recordings remain read-only; analysis artifacts go to a separate project directory.

## 3. Three-minute first run

1. Choose **Example projects** on the home page.
2. Open a teaching simulation.
3. Go to **02 Raw quality control** and run the node.
4. Read the result and “How to interpret” text. Double-click an axis to open Figure Studio.
5. Press `Ctrl+S`, close the app, then restore the project by opening its `neuroflow_project.json`.

Use `Ctrl+Shift+H` for the searchable tutorial center and `Ctrl+K` for command search.

## 4. Import your own data

Choose **New project**, then select the correct source:

- interleaved `.bin`, `.dat`, or `.raw` with sampling rate, channel count, dtype, gain, and layout;
- Intan, Open Ephys, SpikeGLX/Neuropixels, Blackrock, Plexon, TDT, or NWB;
- existing Kilosort/Phy, IBL ALF, NWB Units, or NEX5 sorting.

Before sorting, verify source, sampling rate, channels, duration, voltage units, probe/contact geometry, and behavior events on **01 Data and project**. Do not guess missing acquisition metadata.

## 5. Import behavior and TTL

Open **06 Event synchronization** and choose **Import/replace behavior and TTL**. A behavior table normally contains trial, condition, event type/code, and `behavior_time`. The TTL table provides the corresponding pulses in the electrophysiology clock.

The application fits `ephys_time = offset + slope × behavior_time` from ordered pulse pairs and stores pulse counts, drift, and residuals. Never assume two devices share a clock without synchronization evidence.

## 6. Analysis workflow

| Stage | Purpose | Main evidence |
|---|---|---|
| 01 Data and project | Validate source and workflow entry | Manifest and provenance |
| 02 Raw QC | RMS, bad channels, saturation, line noise | QC figures and channel table |
| 03 Preprocessing | Filtering, reference, preview | Parameters and rebuildable cache |
| 04 Spike sorting | Run a selected sorter | Native output and unified spike times |
| 05 Unit quality | Waveform, ISI, SNR, drift, manual labels | Screening and curation records |
| 06 Event synchronization | Map behavior time to ephys time | Aligned events and synchronization QC |
| 07 Behavior | Trials, choices, accuracy, reaction time | Behavior figures and tables |
| 08 Neural activity | Raster, PSTH, population dynamics | Neural-response figures |
| 09 Statistics | Effect sizes, permutation, bootstrap, multiplicity | Tables and methods |
| 10 Machine learning | Classification, regression, decoding, clustering | Cross-validation and permutation baselines |
| 11 Publication and reproduction | English main/supplementary figures, legends, Methods | Publication report and provenance |

Stages are modular. A project with existing sorting may begin at Unit quality instead of rerunning raw processing.

## 7. Compare three sorters

Run Kilosort4, MountainSort5, and SpyKING CIRCUS2 on the same recording, channels, sampling rate, and time interval. Open **Unified sorter results and comparison** to inspect counts, provenance, matching, and agreement.

Real recordings have no ground truth. Precision, recall, and F1 between two sorter outputs describe agreement, not biological accuracy. Review every candidate in **05 Unit quality** before calling it a single unit.

## 8. Figures and publication export

- Click a plotted element to inspect its value; double-click an axis or use **Edit panel** to open Figure Studio.
- **Selected object** edits one element; **Shared style** applies consistent typography, axes, grid, and color rules across project figures.
- **Publication and reproduction** creates English main/supplementary storyboards, panel letters, draft legends, Methods, file inventory, and checksums.
- Automated layout does not replace scientific, statistical, visual, or target-journal review.

## 9. Multi-session and multi-animal studies

One project represents one session. First curate units, synchronize behavior, and
run event-aligned analysis with the same definitions, windows, and bins in every
project. Then choose **File > Multi-session study…**:

1. Create a Study and add each `neuroflow_project.json`.
2. Verify biological animal IDs, unique session IDs, inclusion, and shared conditions.
3. Choose two shared conditions, whole-animal/session holdout, a model, and permutations.
4. Inspect held-out-group performance, confusion, session effects, and descriptive trajectories.
5. Find English SVG/PNG, CSV, and JSON output under `results/multi_session` in the Study.

Equal Unit IDs across sessions are not matched cells. With one animal, validation can
hold out sessions but cannot establish cross-animal generalization. LDA is a classifier;
latent dynamics is a separate PCA plus regularized linear-transition description. See
the [method guide](MULTI_SESSION_ANALYSIS_ZH.md) and the English web manual.

## 10. AI assistant and institute harness

Open **Help > AI settings** and choose Manual, Assistant, or Collaborative mode. If DeepSeek Harness is installed locally, choose **Import installed DeepSeek Harness**, then run **Check service**. NeuroEphys AI imports only non-secret endpoint, model, and environment-variable metadata; it never opens the Harness credential file.

The assistant uses a versioned, constrained project-summary contract rather than automating the Harness web interface. Raw voltage and local paths are excluded. In Collaborative mode the model can only propose whitelisted tools; the App validates the request locally and asks for confirmation according to risk.

Answers default to **Concise** view: conclusion first, no more than three key points, project-evidence status, the next step, and important warnings. The full scientific explanation, limitations, evidence identifiers, and proposed actions remain available through **View full answer and evidence**. Switch **Answer view** to **Full** when reviewing every detail.

The app supplies a versioned, constrained project context: current stage, completed evidence, outputs, limitations, and registered tools. Raw voltage, large arrays, local paths, and identity data are excluded by default. Collaboration-mode actions remain allowlisted and require local validation and user confirmation. Deterministic analysis continues when AI is unavailable.

After a Study is saved, AI can read its redacted ID, counts, conditions, validation
design, and result summary and can propose a controlled run in Collaborative mode.
Paths, animal/session rows, raw voltage, and large arrays are excluded.

## 11. Project layout

| Path | Contents |
|---|---|
| `neuroflow_project.json` | App project entry point |
| `inputs/` | Source index and import metadata |
| `config/` | Parameters and versions |
| `cache/`, `derived/` | Rebuildable intermediates |
| `results/` | Native sorter outputs and comparisons |
| `exports/` | Figures, tables, reports, publication packages |
| `logs/` | Run logs, experiment notes, and manual notes |

Back up the entire project directory together with the source data. A copied figure alone is not a reproducible project.

## 12. Python installation

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install neuroephys_ai-1.3.1-py3-none-any.whl
neuroephys info --json
```

```python
from pathlib import Path
import neuroephys as ne

project = ne.create_simulated_project(Path("example_project"))
quality = ne.run_raw_qc(project)
print(quality["quality_score"])
```

See the [README](../README.md) and [Python package manual](https://carbonlack.github.io/neuroflow-ai/en/python-package.html) for optional dependencies and additional APIs.

## 13. Troubleshooting

- **Missing DLL at startup:** reinstall or fully extract the portable ZIP; do not copy only the EXE.
- **Kilosort unavailable:** verify the Full edition, NVIDIA driver, CUDA/PyTorch detection, and GPU memory, or choose a CPU sorter.
- **Project does not open:** choose `neuroflow_project.json` from the project root.
- **Behavior event count is wrong:** check event codes, time units, duplicate rows, synchronization pulses, and clock mapping.
- **Small window clips content:** collapse either sidebar and drag the splitters; dialogs and tutorials support scrolling.
- **AI cannot connect:** check the base URL (often ending in `/v1`), model, key, and service-status response. AI failure does not disable deterministic analysis.

More help: [Chinese manual](https://carbonlack.github.io/neuroflow-ai/zh/) · [English manual](https://carbonlack.github.io/neuroflow-ai/en/) · [GitHub Issues](https://github.com/CarbonLack/neuroflow-ai/issues)
