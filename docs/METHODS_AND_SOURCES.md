# NeuroFlow methods and source register

This register records why a method appears in NeuroFlow, which source defines it,
and what NeuroFlow implemented independently. It is not a copy ledger: no external
interface, tutorial paragraph, figure, or source-code block is reproduced in the
application.

## Source policy

1. Official documentation defines supported APIs and data contracts.
2. Original papers define scientific methods and limitations.
3. Secondary articles are used only to discover topics and source literature.
4. NeuroFlow writes its own adapters, validation rules, interface, figures, and
   tutorials.
5. A case template never claims to reproduce a paper unless it runs the paper's
   data and prespecified analysis with matching validation.

## Primary sources

| Source | Role in NeuroFlow | Independent implementation |
|---|---|---|
| [SpikeInterface overview](https://spikeinterface.readthedocs.io/en/stable/) | Recording/sorting framework and modular workflow boundaries | NeuroFlow desktop navigation, import validation, sorter workbench and audit model |
| [SpikeInterface preprocessing](https://spikeinterface.readthedocs.io/en/stable/modules/preprocessing.html) | Lazy chains, `PreprocessingPipeline`, bad-channel handling, phase shift, referencing and whitening | AP/LFP branch preview, guardrails, candidate-channel review and project provenance |
| [SpikeInterface postprocessing](https://spikeinterface.readthedocs.io/en/stable/modules/postprocessing.html) | `SortingAnalyzer` extensions and dependency relationships | Human-readable extension/status presentation and workflow integration |
| [SpikeInterface comparison](https://spikeinterface.readthedocs.io/en/stable/modules/comparison.html) | Ground-truth, symmetric two-sorter, and multi-sorter comparison definitions | Normalized sorter registry, Hungarian matched/unique Unit view, consensus summary, and ground-truth-only performance labels |
| [Kilosort documentation](https://kilosort.readthedocs.io/en/latest/) | Kilosort4 parameters, outputs and diagnostics | NeuroFlow parameter presets, output browser, runtime logging and simulation validation |
| [MountainSort5 0.5.9](https://pypi.org/project/mountainsort5/) | Current package, Isosplit dependency, SpikeInterface I/O, CPU execution and three sorting schemes | Windows environment probe, SpikeInterface adapter, normalized output, audit trail and cross-sorter comparison |
| [Neo data model](https://neo.readthedocs.io/en/stable/read_and_analyze.html) | Unit-aware `AnalogSignal`, `SpikeTrain`, `Event`, `Epoch`, `Block` and `Segment` | Conversion from NeuroFlow projects into Neo objects without changing the project schema |
| [Elephant module reference](https://elephant.readthedocs.io/en/stable/modules.html) | Spike-train, spectral, synchrony and spike-field APIs | Curated desktop analysis views, result storage, explanation and cross-stage validation |
| [Folschweiller & Sauer, 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10312056/) | Scientific example combining respiration, LFP, spikes, coherence, phase and PAC | Synthetic three-state validation case with different data and original figures; no numerical reproduction claim |
| [IBL Brain-Wide Map](https://www.internationalbrainlab.com/brainwidemap) | Public-data organization and behavior/neural analysis examples | Local ALF import and method-to-panel mapping |

## Secondary reading supplied by the project owner

The following WeChat articles helped identify topics that should be checked
against official documentation and original papers. NeuroFlow does not copy their
text, code, screenshots, or figures.

| Article | How it was used |
|---|---|
| [基于 SpikeInterface 的 Spike Sorting 管线](https://mp.weixin.qq.com/s/ymhGYp_Ji7AC_-dfp1_c5g) | Checklist for independently verifying the sorting-stage coverage against SpikeInterface |
| [严谨神经数据分析管线（下）：统计检验](https://mp.weixin.qq.com/s/DuAqu3d6YKlSqp8EmUKH2Q) | Prompted verification of repeated designs, nonparametric tests, circular statistics and surrogate tests in the original paper |
| [在体电生理数据处理管线概览及常用图表](https://mp.weixin.qq.com/s/JL220OvJQoRIwnK7o-qu9A) | Topic index for QC, LFP, unit review and spike-field views; thresholds were not imported |
| [严谨神经数据分析管线（上）：多通道分析](https://mp.weixin.qq.com/s/ss3_wFmS_Tun9Z0w1i6ykQ) | Led to the original respiration/PFC paper and its Materials and Methods section |
| [使用 Elephant 进行 Spike 和 LFP 综合分析](https://mp.weixin.qq.com/s/gzkDSacyi-p1MHbdhuBbRQ) | Topic index cross-checked against the Elephant function reference |

## Implemented Elephant tranche

| Analysis | API/provider | Stored result |
|---|---|---|
| Rate and interval variability | Elephant `mean_firing_rate`, `isi`, `cv`, `cv2`, `lv`, `lvr` | Per-unit table |
| Across-trial count variability | Elephant `fanofactor` | Per-unit trial Fano factor |
| Binned relationships | Elephant `BinnedSpikeTrain`, correlation and CCH | Correlation matrix and lag histogram |
| Timing relationships | Elephant STTC, Victor-Purpura and van Rossum distances | Pairwise matrices |
| LFP spectrum | Elephant Welch PSD | Frequency-by-channel power |
| LFP relationship | Elephant Welch coherence and phase lag | Frequency curves |
| Spike-field phase | Elephant Hilbert and spike-triggered phase | Preferred phase and vector strength |
| Significance | NeuroFlow circular shift plus Rayleigh approximation | Per-unit p values and recorded surrogate count |
| PAC case | NeuroFlow/SciPy, method structure based on the cited paper | Phase-binned gamma amplitude and KLD |

Advanced Elephant methods such as SPADE, ASSET, Unitary Event Analysis, CAD,
CuBIC and GPFA remain catalogued rather than presented as one-click validated
analyses. Their scientific assumptions and performance costs require dedicated
task templates.
