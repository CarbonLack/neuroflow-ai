"""Short, task-oriented help that follows the desktop application's real controls.

Keep this catalogue free of Qt and HTML so the desktop help and the website can
share its text. ``page_key`` names a workflow stage, not an action to execute.
Opening a tutorial must never start an analysis or replace project data.
"""

from __future__ import annotations

from typing import Any


def _step(title: str, title_en: str, body: str, body_en: str) -> dict[str, str]:
    return {"title": title, "title_en": title_en, "body": body, "body_en": body_en}


START = ("开始项目", "Getting started")
PREPARE = ("质控与排序", "QC and sorting")
ANALYSE = ("分析与出图", "Analysis and figures")
WORKSPACE = ("保存与工作区", "Saving and workspace")


def _guide(
    key: str,
    title: str,
    title_en: str,
    category: tuple[str, str],
    page_key: str | None,
    summary: str,
    summary_en: str,
    prerequisites: str,
    prerequisites_en: str,
    steps: list[dict[str, str]],
    check: str,
    check_en: str,
    output: str,
    output_en: str,
    troubleshooting: list[dict[str, str]],
    reference: str = "",
) -> dict[str, Any]:
    return {
        "id": key,
        "title": title,
        "title_en": title_en,
        "category": category[0],
        "category_en": category[1],
        "page_key": page_key,
        "summary": summary,
        "summary_en": summary_en,
        "prerequisites": prerequisites,
        "prerequisites_en": prerequisites_en,
        "steps": steps,
        "check": check,
        "check_en": check_en,
        "output": output,
        "output_en": output_en,
        "troubleshooting": troubleshooting,
        "reference": reference,
    }


TUTORIAL_CATALOG: list[dict[str, Any]] = [
    _guide(
        "examples", "先用示例熟悉操作", "Try an example", START, None,
        "没有自己的数据也可以开始。建议先打开 8 通道微丝教学示例。",
        "Start without your own recording. The 8-channel microwire teaching example is a good first run.",
        "教学模拟在本机生成；已验证公开项目首次打开可能需要联网下载。",
        "Teaching data are generated locally. A verified public project may need a download on first use.",
        [
            _step("打开示例库", "Open the example library", "选择“文件 → 示例项目…”，或点击首页“示例项目”。", "Choose File → Example projects… or Example projects on the home page."),
            _step("选择一套数据", "Choose a dataset", "选择教学模拟行，点击“打开所选示例”。公开项目也在同一个列表里，可根据内容和可用状态选择。", "Select a teaching row and click Open selected example. Public projects are in the same list; check their contents and availability."),
            _step("完成第一次分析", "Run your first analysis", "先查看“原始质控”，再到“Spike sorting”选择环境可用的 sorter，运行本步骤。每次完成后看图和结果再继续。", "Inspect Raw QC, then select an available sorter in Spike sorting and run that stage. Review each result before moving on."),
        ],
        "左侧流程可直接切换。“下一步”切换页面，“运行”才会计算。",
        "The left workflow provides direct navigation. Next changes the page; Run performs a calculation.",
        "示例会成为普通项目；从“文件 → 打开项目文件夹”查看保存位置。",
        "The example opens as an ordinary project. Use File → Open project folder to find its location.",
        [_step("示例没有原始波形", "No raw traces in an example", "部分公开项目只有已排序 Units 和行为数据。可从 Unit 质控和下游分析开始。", "Some public projects contain sorted units and behavior only. Start at Unit QC or downstream analysis.")],
    ),
    _guide(
        "import", "导入自己的原始记录", "Import a raw recording", START, "import",
        "从采集文件或通用二进制建立项目，导入后先核对记录信息和波形。",
        "Create a project from acquisition files or generic binary, then check recording metadata and traces.",
        "原始文件、采样率、通道数、数据类型、增益和探针信息。设备文件通常自带一部分信息。",
        "Recording files, sampling rate, channel count, dtype, gain, and probe information. Acquisition files often supply some metadata.",
        [
            _step("选择数据入口", "Choose an input", "点击首页“新建项目”，选择记录系统文件或通用二进制。已打开的空项目可用“数据与项目 → 导入我的电生理数据”。", "Click New project on the home page and select acquisition files or generic binary. In an open empty project, use Data and project → Import my electrophysiology data."),
            _step("核对读取参数", "Verify reading parameters", "设备记录选对应读取器。通用 .bin/.dat 核对采样率、通道数、dtype、μV/bit；即使从 params.py 自动带入也要确认。Open Ephys 未指定数据流时会尝试选择 AP。", "Select the acquisition reader. For .bin/.dat, verify rate, channels, dtype, and μV/bit, including values detected from params.py. Open Ephys attempts AP selection when no stream is specified."),
            _step("查看第一次读取结果", "Inspect the imported recording", "创建后检查“数据与项目”的来源、时长和通道数，移动波形时间窗，确认不同通道的信号正常。随后进入“原始质控”。", "Check the source, duration, and channel count in Data and project. Move through the trace time window and verify channels before opening Raw QC."),
        ],
        "用采集软件的记录信息核对参数；采样率或通道数错误会让时间和波形一起出错。",
        "Check parameters against the acquisition software. An incorrect rate or channel count distorts timing and traces.",
        "项目保存来源索引、读取参数和可用缓存。位置见“文件 → 打开项目文件夹”。",
        "The project stores source links, reading parameters, and available caches. Find them with File → Open project folder.",
        [_step("Open Ephys 提示多个数据流", "Multiple Open Ephys streams", "在导入窗口填写所需 stream_id；AP 用于 spike 分析，LFP 数据流用于低频分析。", "Enter the required stream_id in the import dialog. Use AP for spikes and the LFP stream for low-frequency analysis.")],
        "https://spikeinterface.readthedocs.io/en/latest/modules/extractors.html",
    ),
    _guide(
        "import_sorting", "接着分析已有排序结果", "Continue from sorted units", START, "import",
        "已有 Kilosort/Phy 或 Offline Sorter 结果，可以直接进入 Unit 质控。",
        "Import Kilosort/Phy or Offline Sorter output and continue with Unit QC.",
        "Kilosort/Phy 结果文件夹及原采样率，或 .nex5 文件。事件分析还需要事件时间。",
        "A Kilosort/Phy output folder and its original sampling rate, or a .nex5 file. Event analysis also requires event times.",
        [
            _step("选择结果格式", "Choose the result format", "在导入窗口选择“已有 sorting 结果”或“Offline Sorter / NeuroExplorer 结果”。", "In the import dialog, choose existing sorting results or Offline Sorter / NeuroExplorer results."),
            _step("核对文件与时间", "Check files and timing", "Kilosort/Phy 选择包含 spike_times.npy 和 cluster 分配的文件夹。NEX5 核对“时间对齐方式”，仅在有实验依据时使用结束时间对齐或手动偏移。", "For Kilosort/Phy, select the folder containing spike_times.npy and cluster assignments. For NEX5, check Time alignment; use end alignment or a manual offset only when justified by the recording."),
            _step("检查候选 Unit", "Inspect candidate units", "导入完成后到“Unit 质控”运行本步骤。若要对比同一记录的不同结果，先打开对应原始记录项目，再向该项目导入结果。", "After import, run Unit QC. To compare results for one recording, first open that recording's project, then import the result into it."),
        ],
        "Unit 数和记录时长应接近原软件显示值。仅有 spike 时间时，原始信号和 LFP 分析可能不可用。",
        "Unit count and duration should agree with the source software. Spike times alone do not provide raw-signal or LFP analysis.",
        "项目保留标准化 spike 时间、来源和可用波形信息，可继续复核、事件分析和导出。",
        "The project retains normalized spike times, provenance, and available waveform information for curation, event analysis, and export.",
        [_step("导入后时长差很多", "Duration differs substantially", "先核对原采样率及 NEX5 时间偏移。不要为配合一张图而随意修改采样率。", "Check the original sampling rate and NEX5 time offset first. Do not adjust sampling rate just to make a plot look right.")],
    ),
    _guide(
        "resume", "打开上次保存的项目", "Resume a saved project", START, "import",
        "用项目清单继续上次的工作，包括已有结果和最后保存的页面。",
        "Resume from the project manifest with saved results and the last saved page.",
        "项目文件夹中的 neuroflow_project.json，以及该项目依赖的原始数据或缓存。",
        "The project's neuroflow_project.json and the raw data or caches it references.",
        [
            _step("打开项目清单", "Open the manifest", "按 Ctrl+O，或选择“文件 → 打开／导入项目…”，找到 neuroflow_project.json。", "Press Ctrl+O or choose File → Open / import project… and select neuroflow_project.json."),
            _step("确认恢复内容", "Check the restored state", "查看项目名称、来源路径和左侧步骤状态。已完成的结果可直接查看；只运行需要更新的步骤。", "Check the project name, source path, and stage status. View completed results directly and run only the stages you need to update."),
            _step("保存这次工作", "Save your work", "按 Ctrl+S。通过“文件 → 打开项目文件夹”检查说明、日志、结果和导出文件。", "Press Ctrl+S. Use File → Open project folder to inspect notes, logs, results, and exports."),
        ],
        "项目清单记录文件位置；单独复制这个 JSON 文件不会复制全部数据。",
        "The manifest records file locations; copying the JSON alone does not copy the dataset.",
        "沿用原项目文件夹；最后保存的工作流页面记录在项目中。",
        "Work continues in the original project folder, with the last saved workflow page recorded.",
        [_step("换电脑后找不到原始记录", "Source missing after moving computers", "查看 inputs/source_index.json 中的来源。恢复对应数据路径；重新分析前确认所需文件可以读取。", "Check the source in inputs/source_index.json. Restore the referenced data location and verify required files can be read before rerunning analysis.")],
    ),
    _guide(
        "qc", "检查原始波形和坏通道", "Inspect traces and channel quality", PREPARE, "qc",
        "用波形、功率图和时间线定位噪声，决定后续需要关注哪些通道与时段。",
        "Use traces, power maps, and a timeline to identify noisy channels and periods.",
        "包含可读取原始电压的项目。",
        "A project with readable raw voltage.",
        [
            _step("运行原始质控", "Run Raw QC", "打开“原始质控”，点击“运行当前所选分析”。等底部状态显示完成。", "Open Raw QC and click Run selected analysis. Wait for completion in the bottom status area."),
            _step("切换诊断视图", "Switch diagnostic views", "在标题旁的下拉框依次查看“质控指标总览”“通道 × 频率功率图”和“记录期间质量时间线”。", "Use the dropdown beside the title to inspect QC metric summary, Channel-by-frequency power, and Quality timeline."),
            _step("返回波形核实", "Verify with traces", "切回“多通道原始波形”，调整时间窗和通道范围，核实提示中的噪声、饱和或异常时段。把确认事项写入项目的人工实验笔记。", "Return to Multichannel raw traces and adjust the time window and channels. Verify noise, clipping, or suspicious periods and record decisions in the project notes."),
        ],
        "质量分是汇总提示。注意检查实际评估时段，不能由一个分数认定整段记录可用。",
        "The score is a summary. Check the evaluated periods; one score cannot establish full-session quality.",
        "质控结果随项目保存；日志和人工笔记位于 logs 文件夹。",
        "QC is saved with the project. Logs and manual notes are under logs.",
        [_step("页面提示没有原始电压", "No raw voltage available", "只有已排序 Units 的项目可直接做 Unit 质控。若需要原始质控，请导入对应采集记录。", "Use Unit QC for a project containing sorted units only. Import the acquisition recording when raw QC is needed.")],
        "https://spikeinterface.readthedocs.io/en/latest/modules/preprocessing.html",
    ),
    _guide(
        "preprocess", "查看 AP 与 LFP 预处理预览", "Preview AP and LFP preprocessing", PREPARE, "preprocess",
        "检查短片段处理前后变化，并查看实际记录的处理链。",
        "Compare a short segment before and after processing and inspect the recorded processing chain.",
        "原始电压和已核实的采集信息；先完成原始质控。",
        "Raw voltage and verified acquisition metadata. Complete Raw QC first.",
        [
            _step("生成预览", "Generate the preview", "进入“预处理”，点击“运行当前所选分析”。这里生成短片段预览。", "Open Preprocessing and click Run selected analysis to generate a short-segment preview."),
            _step("按分析对象查看", "Choose the signal branch", "切换“AP / sorting 分支”或“LFP 分支”，对比波形与频谱。", "Switch between AP / sorting branch and LFP branch and compare traces and spectra."),
            _step("核对处理链", "Check the processing chain", "查看“可审计处理链与安全检查”。到 sorting 页后，再核对所选 sorter 的输入说明和内部处理。", "Open Auditable chain and safeguards. On the sorting page, also read the selected sorter's input contract and internal processing."),
        ],
        "本页预览不会把已白化数据再交给 Kilosort4。当前预览使用的参数以处理链记录为准。",
        "This preview does not feed pre-whitened data to Kilosort4. The processing-chain record lists the preview parameters.",
        "预览结果和处理参数保存到项目，可重新打开查看。",
        "Preview results and processing parameters are stored in the project for later inspection.",
        [_step("想修改滤波或参考参数", "Need different filter or reference settings", "先查看处理链。当前桌面预览并非任意处理链编辑器；高级参数可由 Python 接口设置，并保留实际参数记录。", "Inspect the chain first. The desktop preview is not a general processing-chain editor; advanced parameters can be set through the Python interface and recorded with the results.")],
        "https://spikeinterface.readthedocs.io/en/latest/modules/preprocessing.html",
    ),
    _guide(
        "sorting", "选择 sorter 并运行", "Select and run a sorter", PREPARE, "sorting",
        "先看环境和探针适用性，再运行一个 sorter；结果可保留用于后续比较。",
        "Check the environment and probe requirements, then run a sorter and retain its output for comparison.",
        "原始电压、正确的采样率和通道几何，以及表中显示可用的 sorter 环境。",
        "Raw voltage, the correct rate and channel geometry, and an available sorter environment.",
        [
            _step("确认 sorter 可用", "Check availability", "打开“Spike sorting”，查看表中的“环境”“硬件”“适用记录”。缺少依赖时打开“编辑 → Sorter 管理…”。", "Open Spike sorting and inspect Environment, Hardware, and Best suited recordings. Use Edit → Sorter manager… if dependencies are missing."),
            _step("选择并核对参数", "Select and verify parameters", "点击要运行的 sorter 行。Kilosort4 可查看预设、batch_size、漂移块和阈值；MountainSort5 可选择方案、检测阈值和训练时长。", "Select the sorter row. Kilosort4 exposes presets, batch_size, drift blocks, and thresholds; MountainSort5 exposes scheme, detection threshold, and training duration."),
            _step("运行并看诊断", "Run and inspect diagnostics", "点击底部运行按钮，确认对话框中的 sorter。完成后用“运行后诊断视图”查看输出，并到“Unit 质控”检查候选 Units。", "Click the bottom Run button and verify the sorter in the confirmation dialog. After completion, use Post-run diagnostic view and continue to Unit QC."),
        ],
        "Simple 适合快速检查流程；正式分析需要结合记录类型选择方法并复核 Units。",
        "Simple is useful for quick workflow checks. Choose a method suited to the recording and curate its units for analysis.",
        "原生结果与日志位于 results 下对应 sorter 的文件夹，统一结果随项目保存。",
        "Native results and logs are under the sorter's folder in results. Normalized output is saved with the project.",
        [_step("运行失败或显存不足", "Failure or insufficient GPU memory", "先读失败提示和日志。Kilosort 可检查 GPU 环境和 batch_size；也可选择表中可用的 CPU sorter 验证输入。", "Read the error and log first. For Kilosort, check the GPU environment and batch_size; an available CPU sorter can also help verify the input.")],
        "https://kilosort.readthedocs.io/en/latest/",
    ),
    _guide(
        "comparison", "横向比较两个 sorting 结果", "Compare sorting results", PREPARE, "sorting",
        "并排查看 Unit 数、spike 数、独有 Unit 和匹配一致度，定位方法差异。",
        "Compare unit counts, spike counts, unique units, and matched agreement to locate method differences.",
        "同一项目内至少两份 sorting 结果；比较前核对来源记录、通道和时间范围。",
        "At least two sorting results in one project. Verify recording identity, channels, and time range first.",
        [
            _step("准备第二份结果", "Add a second result", "在同一原始记录项目运行另一个 sorter，或导入该记录的外部排序结果。", "Run another sorter in the same recording project or import an external sorting result for that recording."),
            _step("打开比较视图", "Open the comparison view", "在“Spike sorting”的“运行后诊断视图”中选择比较视图，然后选择要比较的结果对。", "In Spike sorting, choose the comparison under Post-run diagnostic view, then select a result pair."),
            _step("查看差异并复核", "Inspect differences", "先看匹配 Unit 和一致度，再看各自独有 Unit。回到 sorter 列表选择要查看的结果，进入 Unit 质控核实波形和稳定性。", "Inspect matches and agreement, then each result's unique units. Select the result in the sorter list and use Unit QC to check waveforms and stability."),
        ],
        "相同输出时窗不等于相同训练时长。真实记录没有真值时，一致度不能解释为准确率。",
        "Matching output windows do not imply identical training durations. Without ground truth, agreement is not an accuracy estimate.",
        "results/sorting_comparison 保存 sorter_summary.csv、pairwise_summary.csv 和比较说明。",
        "results/sorting_comparison contains sorter_summary.csv, pairwise_summary.csv, and interpretation notes.",
        [_step("比较列表为空", "No result pairs listed", "确认两份结果都保存在当前项目。来自不同记录的结果不应混放后直接比较。", "Confirm both results are saved in the current project. Do not combine unrelated recordings for comparison.")],
        "https://spikeinterface.readthedocs.io/en/latest/modules/comparison.html",
    ),
    _guide(
        "unit_qc", "逐个复核 Unit 并保存判断", "Review and label units", PREPARE, "unit_qc",
        "将自动指标与波形、ISI 和稳定性一起查看，保存自己的复核结论。",
        "Review automated metrics alongside waveforms, ISIs, and stability, then save a curation decision.",
        "已运行或导入 sorting 结果；波形诊断取决于导入文件中可用的信息。",
        "A completed or imported sorting result. Waveform diagnostics depend on available data.",
        [
            _step("计算 Unit 指标", "Calculate Unit metrics", "进入“Unit 质控”并运行本步骤。标题旁可切换“Unit 指标总览”或某个 Unit 的波形/ACG/ISI/稳定性。", "Open Unit QC and run the stage. Use the title dropdown for Unit metric overview or one unit's waveform/ACG/ISI/stability."),
            _step("打开人工复核", "Open manual curation", "点击“打开人工 Unit 复核工作台”。左侧选择 Unit，中间查看诊断，右侧填写“人工分类”“置信度”和“复核人”。", "Click Open manual Unit curation. Select a unit on the left, inspect the center plots, and set Decision, Confidence, and Reviewer on the right."),
            _step("记录判断依据", "Save the evidence", "勾选已检查的证据，写入“复核备注”，点击“保存本 Unit 结论”，然后查看下一个 Unit。", "Check the evidence you reviewed, enter Notes, click Save decision, and move to the next unit."),
        ],
        "分类和备注会保存；当前工作台不提供 cluster 合并或拆分操作。缺失指标不能作为通过证据。",
        "Labels and notes are saved. This workbench does not merge or split clusters; missing metrics are not passing evidence.",
        "复核记录随项目保存；导出时可保留人工结论及其依据。",
        "Curation records are saved with the project and can be included in exported results.",
        [_step("人工复核按钮不可用", "Curation button unavailable", "先确认有 sorting 结果，再运行 Unit 质控生成指标。", "Confirm a sorting result is loaded, then run Unit QC to calculate metrics.")],
        "https://spikeinterface.readthedocs.io/en/latest/modules/qualitymetrics.html",
    ),
    _guide(
        "sync", "把行为事件对齐到电生理时间", "Align behavior to the recording", ANALYSE, "sync",
        "导入行为文件和同步脉冲，核对时间换算后再做事件响应。",
        "Import behavior and synchronization pulses, then verify timing before event-response analysis.",
        "通用事件 CSV 或 MED-PC C/D 数组；如使用独立行为时钟，还需要对应 TTL。",
        "A generic event CSV or MED-PC C/D arrays. A separate behavior clock also needs corresponding TTL pulses.",
        [
            _step("导入行为与 TTL", "Import behavior and TTLs", "进入“事件同步”，点击“导入 / 替换行为与 TTL”，选择格式和文件。Open Ephys 可读取采集系统数字输入。", "Open Event synchronization and click Import / replace behavior and TTL. Select the format and files; Open Ephys can supply recorded digital inputs."),
            _step("核对时钟来源", "Check clock sources", "CSV 核对时间单位；MED-PC 核对行为同步事件码和采集系统 TTL 通道。保存后运行当前步骤。", "Check CSV time units. For MED-PC, verify the behavior synchronization code and recorded TTL channel, then save and run this stage."),
            _step("检查对齐结果", "Inspect alignment", "查看脉冲数、匹配数量、时间偏移、漂移和残差。检查事件是否落在记录范围内。", "Inspect pulse counts, matches, offset, drift, and residuals. Verify that events fall within the recording."),
        ],
        "缺脉冲、重复脉冲或错误通道会影响按顺序配对的结果。先修正事件来源再解释神经活动。",
        "Missing or duplicate pulses and an incorrect channel affect ordered pairing. Correct event inputs before interpreting neural responses.",
        "导入配置、对齐记录、事件和可定义的 trial 随项目保存。",
        "Import settings, alignment records, events, and defined trials are stored in the project.",
        [_step("有事件但没有 trial", "Events without trials", "事件列表不一定包含明确 trial 边界。先检查行为文件是否提供 trial 定义；可用事件时间不代表行为表现指标都可计算。", "An event list may lack trial boundaries. Check whether the behavior file defines trials; event timing alone does not supply every behavioral measure.")],
    ),
    _guide(
        "behavior", "检查行为与有效 trial", "Inspect behavior and trials", ANALYSE, "behavior",
        "先确认行为数据是否完整，再判断哪些条件适合做神经比较。",
        "Check behavioral completeness before choosing conditions for neural comparisons.",
        "已导入行为事件；反应时、选择和心理测量分析需要对应 trial 字段。",
        "Imported behavior events. Reaction time, choice, and psychometrics require their corresponding trial fields.",
        [
            _step("生成行为摘要", "Generate the summary", "打开“行为分析”，运行本步骤。查看当前事件数、trial 数和行为图。", "Open Behavior analysis and run this stage. Inspect event count, trial count, and the behavior plots."),
            _step("核对条件和样本数", "Check conditions and sample sizes", "查看各条件的 trial 数、可用反应时和选择。样本太少或字段缺失时，先检查原始行为文件。", "Review trial counts by condition and available reaction times and choices. Check the source behavior file when samples or fields are missing."),
            _step("再选择神经分析", "Choose the neural analysis", "确认需要对齐的事件和要比较的条件后，进入“神经活动”。", "After identifying the alignment event and conditions, continue to Neural activity."),
        ],
        "仅导入事件时间不会自动产生实验选择、正确率或反应时。空白面板应先检查输入字段。",
        "Event times alone do not supply choices, accuracy, or reaction times. Check source fields when a panel is empty.",
        "行为摘要保存在项目中；运行“论文与复现”后可查看相关导出。",
        "Behavior summaries are saved with the project; run Publication and reproducibility for related exports.",
        [_step("反应时或心理测量图为空", "Empty reaction-time or psychometric plot", "查看 trial 定义与字段是否齐全。若仅有离散事件，可先使用事件相关分析。", "Check trial definitions and required fields. With discrete events only, start with event-related neural analysis.")],
    ),
    _guide(
        "analysis", "选择神经分析与事件响应", "Choose a neural analysis", ANALYSE, "analysis",
        "同一个页面提供多种分析，用标题旁的下拉框选择你这次要回答的问题。",
        "One page offers several analyses. Use the dropdown beside the title to choose the question for this run.",
        "Spike 分析需要 Units；事件响应需要事件时间；LFP 与 spike-field 分析需要可用电压。",
        "Spike analysis needs units, event responses need event times, and LFP or spike-field analysis needs available voltage.",
        [
            _step("选择分析对象", "Select the analysis", "查看单 Unit 事件响应选“事件 · Unit …”；比较 spike train 选统计或关系；群体、精细时序和 LFP 各有独立选项。", "Choose Event · Unit … for a unit's event response; choose spike-train statistics or relationships for spike analyses. Population, fine timing, and LFP have separate entries."),
            _step("运行所选分析", "Run the selected analysis", "点击“运行当前所选分析”。群体动态和精细时序会打开设置窗口；其他选项使用当前项目和方法的参数。", "Click Run selected analysis. Population dynamics and fine timing open settings dialogs; other choices use current project and method parameters."),
            _step("核对图和表", "Inspect plots and tables", "事件响应查看 Raster 和 PSTH，核对横轴事件零点与有效 trial 数。切换选项查看对应结果，用图形工具缩放。", "For event responses, inspect the raster and PSTH, alignment zero, and valid trial count. Switch views for related results and zoom with the plot toolbar."),
        ],
        "页面下拉框同时承担分析选择和结果切换；更换选项后看底部“当前”说明，再决定是否运行。",
        "The dropdown selects analyses and result views. Check the bottom Current description after changing it before running.",
        "已完成分析保存在项目中；图表可通过“论文与复现”导出。",
        "Completed analyses are retained in the project; export plots through Publication and reproducibility.",
        [_step("页面仍显示待运行", "A view still shows pending", "确认该类别已经运行且输入齐全。完成事件响应不会自动完成 LFP、群体或精细时序分析。", "Check that this analysis category has run and has the required input. Event responses do not automatically calculate LFP, population, or fine-timing results.")],
    ),
    _guide(
        "population", "比较群体响应与 PCA 轨迹", "Compare population responses", ANALYSE, "analysis",
        "按事件或条件查看多个 Units 的热图、单 trial 响应和群体轨迹。",
        "Inspect multi-unit heatmaps, single-trial responses, and population trajectories by event or condition.",
        "可用 Units 和事件；条件比较需要已有条件标签。",
        "Units and events; condition comparisons require condition labels.",
        [
            _step("打开群体分析", "Open population analysis", "在“神经活动”选择任意“群体动态”选项，点击“运行当前所选分析”。", "In Neural activity, choose a Population dynamics entry and click Run selected analysis."),
            _step("设置本次范围", "Set the analysis scope", "在弹出的设置窗口核对事件、Unit 范围、分析窗口、分箱和基线。排序规则决定热图行的排列。", "In the settings dialog, check events, unit scope, analysis window, bins, and baseline. The ordering rule controls heatmap rows."),
            _step("查看四种结果", "Inspect the result views", "运行后切换“排序热图”“单 trial”“条件比较”和“PCA 轨迹”，确认各视图使用的条件与时间范围一致。", "After running, switch among Ordered heatmap, Single trial, Condition comparison, and PCA trajectory. Check conditions and time ranges across views."),
        ],
        "标准化后的热图颜色表示相对变化；查看图例，避免把它直接解释为 Hz。",
        "Normalized heatmap colors represent relative changes. Check the legend before interpreting them as Hz.",
        "群体分析结果及运行参数保存在项目；可单独保存需要的图面板。",
        "Population results and run settings are saved in the project. Individual figure panels can also be saved.",
        [_step("部分事件被排除", "Some events are excluded", "检查事件靠近记录首尾时，分析窗口是否超出记录范围；同时核对事件和 Unit 筛选。", "Check whether windows around early or late events exceed the recording, and verify event and unit filters.")],
    ),
    _guide(
        "connectivity", "检查毫秒级时序关系", "Inspect fine spike timing", ANALYSE, "analysis",
        "比较 Unit 对的 CCG 与抖动校正结果，再看空间或跨区域分布。",
        "Compare unit-pair CCGs and jitter-corrected results, then inspect spatial or cross-region patterns.",
        "多个可用 Units；空间分析还需要可信通道位置和脑区标记。",
        "Multiple units. Spatial analysis also needs trustworthy positions and region labels.",
        [
            _step("选择精细时序", "Choose fine timing", "在“神经活动”选择“精细时序 · CCG 与抖动校正”，点击运行。", "In Neural activity, select Fine timing · CCG and jitter correction and click Run."),
            _step("核对成对比较设置", "Check pair settings", "在设置窗口确认 Unit 对、时间范围、分箱、抖动与显著性设置。Units 很多时先缩小比较范围。", "Check unit pairs, time range, bins, jitter, and significance in the settings dialog. Restrict the scope first when many units are present."),
            _step("检查单对再看网络", "Inspect pairs before the network", "先看单对 CCG 和校正结果，再切换“空间/跨区域网络”及“距离与延迟统计”。", "Inspect individual CCGs and corrected results before switching to Spatial/cross-region network and Distance and latency statistics."),
        ],
        "时序关系会受到共同输入和放电率变化影响；显著 CCG 不能单独确认突触连接。",
        "Shared input and firing-rate changes affect timing relationships. A significant CCG alone does not establish a synapse.",
        "Unit 对结果、运行设置和网络统计随项目保存。",
        "Pair results, run settings, and network summaries are saved with the project.",
        [_step("距离或脑区信息缺失", "Missing distance or region information", "先核对导入的探针几何和脑区标记；信息不足时仍可检查时间关系，但不能解释空间结果。", "Check probe geometry and region labels. Temporal relationships may still be examined, but missing metadata prevents spatial interpretation.")],
    ),
    _guide(
        "statistics", "查看条件差异与统计依据", "Inspect statistical evidence", ANALYSE, "statistics",
        "将条件差异、效应量和样本结构一起查看，确认检验适合你的实验。",
        "Review condition differences, effect sizes, and sample structure together to assess the test's suitability.",
        "已完成相应神经分析，具有可比较的条件或配对响应。",
        "Completed neural analysis with comparable conditions or paired responses.",
        [
            _step("运行统计套件", "Run the statistical suite", "进入“统计检验”，点击“运行当前所选分析”。", "Open Statistical tests and click Run selected analysis."),
            _step("先看研究设计", "Inspect the design first", "切换“样本层级与检验决策”，核对样本是 trial、Unit、session 还是动物，以及是否属于配对测量。", "Choose Sampling hierarchy and test decisions. Check whether samples are trials, units, sessions, or animals and whether measurements are paired."),
            _step("查看效应与检验", "Inspect effects and tests", "用“条件检验与效应量”和“效应量与多重比较”检查效应方向、置信区间和校正值；有需要再看分布或相位检验。", "Use Condition tests and effects and Effects and multiplicity to inspect effect direction, confidence intervals, and corrected values; inspect distribution or phase tests as needed."),
        ],
        "本页下拉框切换统计结果视图，不是所有检验参数的编辑器。多只动物或多 session 的设计需要核实输入层级。",
        "The dropdown switches result views; it is not an editor for every test parameter. Verify grouping for multi-animal or multi-session designs.",
        "统计结果随项目保存；完整导出提供相关表格和方法记录。",
        "Statistics are saved with the project; full export includes related tables and method records.",
        [_step("检验无法计算", "A test cannot be computed", "检查有效样本量、条件是否齐全、是否有常数列或缺失值。查看具体提示后处理输入。", "Check valid sample counts, conditions, constant columns, and missing values. Use the reported reason to correct inputs.")],
    ),
    _guide(
        "decoding", "运行分类或回归模型", "Run classification or regression", ANALYSE, "decoding",
        "比较神经特征能否预测任务变量，同时检查交叉验证和基线。",
        "Test whether neural features predict a task variable and inspect cross-validation and baseline results.",
        "有效 trial、神经特征及要预测的分类标签或连续行为变量。",
        "Valid trials, neural features, and classification labels or a continuous behavior target.",
        [
            _step("选择任务和模型", "Choose the task and model", "进入“机器学习”，在标题旁选择“分类 · …”或“回归 · …”。分类预测类别，回归预测连续数值。", "Open Machine learning and select Classification · … or Regression · … beside the title. Classification predicts categories; regression predicts continuous values."),
            _step("运行当前模型", "Run the model", "点击“运行当前所选分析”，核对确认窗口中的模型名称。", "Click Run selected analysis and verify the model name in the confirmation dialog."),
            _step("核对验证结果", "Check validation results", "分类查看混淆矩阵、交叉验证和置换基线；回归查看预测与实测及误差。比较模型时使用相同数据范围。", "For classification, inspect confusion, cross-validation, and permutation baseline; for regression, inspect predictions versus observations and errors. Compare models on the same data scope."),
        ],
        "结果中的实际特征、样本数和拆分方式需要核对。PCA 可视化和较高分数本身都不能证明因果关系。",
        "Verify the actual features, sample count, and split strategy in the results. Neither a PCA plot nor a high score establishes causality.",
        "模型评估与参数随项目保存，可从“论文与复现”导出。",
        "Model evaluations and parameters are saved with the project and exported through Publication and reproducibility.",
        [_step("样本或标签不足", "Insufficient samples or labels", "返回行为分析核对有效 trial 与条件数量。不要通过复制 trial 来凑够交叉验证样本。", "Return to Behavior analysis and check valid trials and conditions. Do not duplicate trials to meet cross-validation sample requirements.")],
        "https://scikit-learn.org/stable/common_pitfalls.html",
    ),
    _guide(
        "export", "保存项目、图和实验记录", "Save projects, figures, and records", WORKSPACE, "export",
        "保存便于下次继续；导出提供便于查阅、编辑和交付的图表与记录。",
        "Save to resume later; export figures, tables, and records for review, editing, and sharing.",
        "一个已打开的项目；要导出的分析应先完成。",
        "An open project with the analyses you want to export completed.",
        [
            _step("保存当前项目", "Save the project", "按 Ctrl+S 或选择“文件 → 保存项目”。保存成功后，可用项目清单继续工作。", "Press Ctrl+S or choose File → Save project. After saving, reopen the manifest to continue later."),
            _step("整理图形输出", "Prepare figures", "在分析页用“图形设置”调整图；需要单幅图时使用面板选择和保存按钮。完整导出请进入“论文与复现”运行本步骤。", "Use Figure settings on analysis pages to adjust plots, or select and save an individual panel. For the full export, run Publication and reproducibility."),
            _step("找到成果和日志", "Find outputs and logs", "选择“文件 → 打开项目文件夹”。看 00_README_项目说明.md；图和表在 exports，分析结果在 results，实验日志与人工笔记在 logs。", "Choose File → Open project folder. Read the file beginning with 00_README_; exports holds figures and tables, results holds analysis output, and logs holds experiment logs and notes."),
        ],
        "交付前打开导出的图核对标题、坐标、单位和统计标记。项目依赖外部原始数据时，备份也要包括这些来源。",
        "Before delivery, inspect exported titles, axes, units, and statistical annotations. Back up external source data when the project depends on them.",
        "neuroflow_project.json、inputs、config、logs、cache、derived、results 和 exports 组成项目记录。",
        "neuroflow_project.json, inputs, config, logs, cache, derived, results, and exports form the project record.",
        [_step("只找到 JSON，没有图", "Only the JSON is present", "“保存项目”与“论文与复现”导出是两项操作。先完成分析，再运行导出并检查 exports。", "Saving the project and running Publication and reproducibility are separate actions. Complete the analysis, run export, and inspect exports.")],
    ),
    _guide(
        "layout_ai", "调整三栏、AI 助手与提示", "Arrange panels, AI, and guidance", WORKSPACE, None,
        "按窗口大小分配流程、图表和 AI 的空间，随时收起或恢复。",
        "Allocate space to workflow, figures, and AI, and collapse or restore panels as needed.",
        "打开项目后即可调整三栏；使用在线 AI 需要在 AI 设置中配置服务。",
        "Open a project to arrange the three columns. Online AI requires a configured service in AI settings.",
        [
            _step("调整三栏宽度", "Resize the columns", "拖动栏间分隔线。按 Ctrl+B 缩略左侧流程，按 Ctrl+J 显示或关闭右侧 AI。三栏可以同时保留。", "Drag the separators. Press Ctrl+B to compact the workflow rail and Ctrl+J to show or hide the right AI panel. All three columns can remain open."),
            _step("按需要使用 AI", "Use AI when needed", "在右侧选择“审查项目”“建议流程”或输入问题；“设置”可选择服务。核对 AI 引用的当前项目和步骤，再采纳建议。", "Choose Review project, Suggest workflow, or type a question on the right. Settings selects the service. Check the project and stage in the AI context before using a suggestion."),
            _step("控制引导和布局", "Control guidance and layout", "按 F1 查看本步引导；在“帮助”取消“自动显示分步骤引导”可停止自动弹出。用“视图 → 恢复三栏默认布局”恢复布局。", "Press F1 for the current step guide. Uncheck Help → Show step guides automatically to stop automatic popups. Use View → Reset three-column layout to restore panel sizes."),
        ],
        "图表缩小时可使用图形工具缩放，或 F11 全屏。AI 建议需要结合实验记录和实际输出核对。",
        "Use plot zoom tools or F11 full screen for small plots. Check AI suggestions against experiment records and actual outputs.",
        "分析结果仍由所选分析操作生成，AI 回复显示在右侧对话区。",
        "Selected analysis operations produce results; AI replies appear in the right conversation panel.",
        [_step("找不到底部运行按钮", "Cannot find the Run button", "先收起右侧或缩略左侧，再调整窗口高度；也可从“分析”菜单运行当前所选分析。", "Hide the right panel or compact the left rail and adjust window height. The Analysis menu also provides Run selected analysis.")],
    ),
]


def catalog_text(item: dict[str, Any], field: str, language: str = "zh_CN") -> str:
    """Return localized plain text without introducing markup into the content."""
    if language == "en_US":
        return str(item.get(f"{field}_en", item.get(field, "")))
    return str(item.get(field, ""))


def tutorial_for_id(key: str) -> dict[str, Any]:
    """Resolve a help topic, falling back to the raw-data entry for old links."""
    return next(
        (item for item in TUTORIAL_CATALOG if item["id"] == key),
        next(item for item in TUTORIAL_CATALOG if item["id"] == "import"),
    )


def search_tutorials(query: str, language: str = "zh_CN") -> list[dict[str, Any]]:
    """Match all words across localized titles, steps, and troubleshooting text."""
    terms = query.casefold().split()
    if not terms:
        return list(TUTORIAL_CATALOG)
    matches = []
    for item in TUTORIAL_CATALOG:
        parts = [
            catalog_text(item, field, language)
            for field in ("title", "category", "summary", "prerequisites", "check", "output")
        ]
        for section in ("steps", "troubleshooting"):
            for step in item[section]:
                parts.extend(catalog_text(step, field, language) for field in ("title", "body"))
        searchable = " ".join(parts).casefold()
        if all(term in searchable for term in terms):
            matches.append(item)
    return matches
