from __future__ import annotations

# Long bilingual help strings are intentionally split across adjacent literals.
# ruff: noqa: ISC004

REFERENCES = (
    {
        "name": "Kilosort4 GUI and parameter guide",
        "url": "https://kilosort.readthedocs.io/en/latest/gui_guide.html",
    },
    {
        "name": "Kilosort4 exported files",
        "url": "https://kilosort.readthedocs.io/en/latest/export_files.html",
    },
    {
        "name": "Kilosort4 drift diagnosis",
        "url": "https://kilosort.readthedocs.io/en/latest/drift.html",
    },
    {
        "name": "Phy visual review workflow",
        "url": "https://phy.readthedocs.io/en/latest/quickstart/",
    },
    {
        "name": "SpikeInterface workflow",
        "url": "https://spikeinterface.readthedocs.io/en/stable/",
    },
    {
        "name": "SpikeInterface preprocessing and pipeline model",
        "url": "https://spikeinterface.readthedocs.io/en/stable/modules/preprocessing.html",
    },
    {
        "name": "SpikeInterface SortingAnalyzer postprocessing",
        "url": "https://spikeinterface.readthedocs.io/en/stable/modules/postprocessing.html",
    },
    {
        "name": "SpikeInterface sorter comparison",
        "url": "https://spikeinterface.readthedocs.io/en/stable/modules/comparison.html",
    },
    {
        "name": "MountainSort5 package and sorting schemes",
        "url": "https://pypi.org/project/mountainsort5/",
    },
    {
        "name": "Neo standard electrophysiology data objects",
        "url": "https://neo.readthedocs.io/en/stable/read_and_analyze.html",
    },
    {
        "name": "Elephant electrophysiology analysis APIs",
        "url": "https://elephant.readthedocs.io/en/stable/modules.html",
    },
    {
        "name": "Folschweiller and Sauer (2023), respiration/PFC study",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10312056/",
    },
    {
        "name": "Plexon Offline Sorter feature reference",
        "url": "https://plexon.com/products/offline-sorter/",
    },
    {
        "name": "GraphPad Prism: ways to change a graph",
        "url": "https://www.graphpad.com/guides/prism/latest/user-guide/how_to_change_a_graph.htm",
    },
    {
        "name": "GraphPad Prism: frame and axes",
        "url": "https://www.graphpad.com/guides/prism/latest/user-guide/frame_and_axes.htm",
    },
    {
        "name": "GraphPad Prism: grid lines",
        "url": "https://www.graphpad.com/guides/prism/latest/user-guide/grid_lines_revised.htm",
    },
    {
        "name": "GraphPad Prism: graph shape and exact size",
        "url": "https://www.graphpad.com/guides/prism/latest/user-guide/graph_shape_and_size.htm",
    },
    {
        "name": "GraphPad Prism: major and minor ticks",
        "url": "https://www.graphpad.com/guides/prism/latest/user-guide/major_and_minor_ticks.htm",
    },
)


CONTROL_HELP = {
    "home.new_project": {
        "zh_CN": (
            "新建空白项目",
            "先选择项目名称和保存位置，只建立项目清单、参数区、结果区和审计记录。"
            "不会生成模拟数据，也不会复制原始文件。项目打开后在“数据与项目”页"
            "明确导入自己的电生理数据。",
        ),
        "en_US": (
            "Create empty project",
            "Choose a project name and location. NeuroFlow creates only the manifest, "
            "parameter, result, and audit structure; it does not generate simulated "
            "data or copy raw files. Import your recording explicitly afterward.",
        ),
    },
    "home.demo": {
        "zh_CN": (
            "打开示例数据",
            "在固定的 DemoData 文件夹生成或复用一份 int16 多通道原始记录，"
            "同时包含 metadata.json、events.csv 和 ground_truth.npz。"
            "打开后可从原始质控一直运行到统计、机器学习和导出。",
        ),
        "en_US": (
            "Open demo data",
            "Create or reuse an int16 multichannel recording in the fixed DemoData "
            "folder, together with metadata.json, events.csv, and ground_truth.npz. "
            "It supports the complete workflow from raw QC through export.",
        ),
    },
    "home.import": {
        "zh_CN": (
            "导入自己的数据",
            "新建项目并进入自己的数据向导。选择“通用二进制、记录系统原始文件"
            "或 Kilosort/Phy 结果”，再填写该格式必需的信息；这里不提供模拟数据，"
            "也不会修改源文件。",
        ),
        "en_US": (
            "Import your own data",
            "Open the format wizard. Choose generic binary, acquisition-system data, "
            "or Kilosort/Phy output, then provide the required metadata. Simulation "
            "is not offered in this route, and source files remain unchanged.",
        ),
    },
    "home.public": {
        "zh_CN": (
            "打开已验证公开项目",
            "打开两套固定版本的公开验证项目：IBL Brain-Wide Map 的指定 eID/PID，"
            "以及 Buzsáki/DANDI 000552 的指定 asset。双击一行即可打开；未下载时"
            "软件会先显示来源、大小和下载确认，不会让用户自行猜测文件结构。",
        ),
        "en_US": (
            "Open verified public project",
            "Open one of two version-locked projects: the specified IBL Brain-Wide "
            "Map eID/PID or the specified Buzsáki/DANDI 000552 asset. Double-click "
            "a row to open it; NeuroFlow confirms any required download first.",
        ),
    },
    "home.restore": {
        "zh_CN": (
            "恢复项目",
            "打开已有 neuroflow_project.json，恢复数据索引、参数、运行状态和结果。"
            "它不会重新复制原始数据。",
        ),
        "en_US": (
            "Restore project",
            "Open an existing neuroflow_project.json and restore source links, "
            "parameters, workflow state, and results without copying raw data again.",
        ),
    },
    "global.language": {
        "zh_CN": (
            "语言",
            "切换整个界面、教程、状态信息和重新生成的图表。已经手工修改过的当前图"
            "会在切换页面后按新语言重新生成。",
        ),
        "en_US": (
            "Language",
            "Switch the interface, tutorials, status text, and newly generated figures. "
            "A manually edited current figure is regenerated after navigation.",
        ),
    },
    "global.save": {
        "zh_CN": (
            "保存项目",
            "写入项目清单、每一步状态、参数和结果索引；不会覆盖原始记录。",
        ),
        "en_US": (
            "Save project",
            "Write the manifest, step states, parameters, and result index without "
            "overwriting the source recording.",
        ),
    },
    "global.run_all": {
        "zh_CN": (
            "运行完整流程",
            "按左侧顺序执行所有可运行节点。高成本的 sorting 会使用 sorting 页当前"
            "选定的工具和参数；缺少原始电压的节点会被明确跳过。开始前弹窗列出"
            "即将运行的节点和 sorter，结束后弹窗汇总完成情况；全过程同时写入右侧审计记录。",
        ),
        "en_US": (
            "Run full workflow",
            "Execute runnable stages in sidebar order. Sorting uses the tool and "
            "parameters currently selected on the sorting page; stages that require "
            "missing raw voltage are explicitly skipped. A confirmation dialog lists "
            "the planned stages and sorter; completion is summarized in another dialog "
            "while the persistent audit log records the full run.",
        ),
    },
    "global.run_step": {
        "zh_CN": (
            "运行当前节点",
            "只执行当前页对应的计算。运行前会校验输入；成功后保存结果并更新状态，"
            "失败时保留此前已完成的数据。运行前确认、成功汇总和失败原因都会弹窗提示，"
            "详细过程仍保留在右侧审计记录中。",
        ),
        "en_US": (
            "Run current stage",
            "Execute only the current page. Inputs are validated first; successful "
            "results are saved and earlier results remain intact on failure. Confirmation, "
            "completion, and failure dialogs provide immediate feedback while details "
            "remain in the audit log.",
        ),
    },
    "plot.style": {
        "zh_CN": (
            "图形呈现",
            "只改变当前图的线型、点或配色，不重新计算数据。标准模式会重新生成图。",
        ),
        "en_US": (
            "Figure presentation",
            "Change lines, markers, or colors for the current figure without "
            "recomputing data. Standard mode regenerates the figure.",
        ),
    },
    "plot.settings": {
        "zh_CN": (
            "Figure Studio 图形工作室",
            "打开对象级编辑器。左侧可选择整图、坐标轴、曲线、散点、柱/填充区域、"
            "热图、文字和图例；右侧按对象提供精确宽高、DPI、标题、单位、范围、颜色、"
            "透明度、粗细、线型、marker、色图、主次刻度、四边坐标轴、主次网格、"
            "参考线和图例设置。修改只影响当前呈现，不重新计算数据。",
        ),
        "en_US": (
            "Figure Studio",
            "Open the object-level editor for the whole figure, axes, lines, scatters, "
            "patches, images, text, and legends. Controls include exact size, DPI, labels, "
            "limits, colors, alpha, widths, styles, markers, colormaps, major/minor ticks, "
            "four independent spines, major/minor grids, reference lines, and legends. "
            "Presentation changes do not recompute data.",
        ),
    },
    "plot.panel": {
        "zh_CN": (
            "子图选择",
            "选择当前多面板图中的一个子图。后续的单独放大、直接编辑和独立保存"
            "只作用于这里选中的子图，不会重新计算分析结果。",
        ),
        "en_US": (
            "Panel selection",
            "Choose one subplot from the current multi-panel figure. Expand, edit, "
            "and save actions target this panel without recomputing results.",
        ),
    },
    "plot.panel_focus": {
        "zh_CN": (
            "单独放大子图",
            "暂时隐藏其他子图，让所选子图占满主画布。放大后仍可使用工具栏缩放、"
            "平移和查看数值；再次点击可恢复全部子图。",
        ),
        "en_US": (
            "Expand selected panel",
            "Temporarily hide other panels and let the selected panel fill the canvas. "
            "Zoom, pan, and value inspection remain available; click again to restore all.",
        ),
    },
    "plot.panel_edit": {
        "zh_CN": (
            "编辑所选子图",
            "打开 Figure Studio 并自动定位到所选坐标轴。可继续选择该子图内的线、"
            "点、柱、热图或文字逐项编辑；不会改变原始数据或数值分析结果。",
        ),
        "en_US": (
            "Edit selected panel",
            "Open Figure Studio focused on the selected axis, then edit its lines, "
            "points, patches, images, or text individually. Numerical results remain unchanged.",
        ),
    },
    "plot.panel_save": {
        "zh_CN": (
            "独立保存子图",
            "只导出当前选中的子图，可选择 SVG、PDF 或 300 dpi PNG。优先使用 "
            "SVG/PDF 继续排版；导出不会覆盖原始分析文件。",
        ),
        "en_US": (
            "Save selected panel",
            "Export only the selected panel as SVG, PDF, or 300 dpi PNG. SVG and PDF "
            "remain suitable for publication layout; source analysis files are unchanged.",
        ),
    },
    "page.option": {
        "zh_CN": (
            "当前页面选项",
            "切换当前页的视图、Unit 或机器学习模型。切换只更新要查看或下一次要运行的"
            "对象，不会自动开始计算，也不会删除已有结果。",
        ),
        "en_US": (
            "Current page option",
            "Choose the current view, unit, or machine-learning model. Selection changes "
            "what is displayed or run next; it does not start computation or delete results.",
        ),
    },
    "trace.start": {
        "zh_CN": (
            "起始时间",
            "决定原始波形预览从记录的第几秒开始。修改后只读取相应片段，不处理全文件。",
        ),
        "en_US": (
            "Start time",
            "Set the recording time at which the raw trace preview begins. Only the "
            "selected segment is read.",
        ),
    },
    "trace.window": {
        "zh_CN": (
            "时间窗",
            "控制横轴显示多少毫秒。较短窗口便于看 spike 波形，较长窗口便于发现伪迹"
            "和慢变化。",
        ),
        "en_US": (
            "Time window",
            "Control the number of milliseconds shown. Short windows reveal spikes; "
            "longer windows reveal artifacts and slow changes.",
        ),
    },
    "trace.channels": {
        "zh_CN": (
            "通道范围",
            "选择第一个通道和同时显示的通道数。用于逐组检查全部通道，不改变数据。",
        ),
        "en_US": (
            "Channel range",
            "Choose the first channel and number of visible channels to inspect the "
            "recording in groups without changing the data.",
        ),
    },
    "trace.gain": {
        "zh_CN": (
            "显示增益",
            "只放大或缩小波形的视觉振幅，不修改原始 ADC 值和后续计算。",
        ),
        "en_US": (
            "Display gain",
            "Scale visual waveform amplitude only; raw ADC values and downstream "
            "computations are unchanged.",
        ),
    },
    "sorting.selector": {
        "zh_CN": (
            "Sorter 选择表",
            "单击一行选择排序器。状态列说明当前电脑能否运行；硬件和适用记录列用于判断"
            "是否匹配当前电极。选择本身不会开始计算。",
        ),
        "en_US": (
            "Sorter selection table",
            "Click a row to select a sorter. Status reports whether this computer can "
            "run it; hardware and recording guidance help assess suitability. "
            "Selection alone does not start computation.",
        ),
    },
    "sorting.preset": {
        "zh_CN": (
            "参数预设",
            "“演示/低通道”关闭漂移校正并使用较大批次；“Neuropixels”启用刚性漂移；"
            "“自定义”保留下方参数。预设会改变真正传给 Kilosort 的值。",
        ),
        "en_US": (
            "Parameter preset",
            "Demo/low-channel disables drift correction and uses longer batches; "
            "Neuropixels enables rigid drift correction; Custom keeps the fields below. "
            "The preset changes values passed to Kilosort.",
        ),
    },
    "sorting.batch_size": {
        "zh_CN": (
            "Kilosort batch_size",
            "每批样本数。30 kHz 下 60000 等于 2 秒；低通道记录可能需要更长批次，"
            "以包含足够 spike 估计漂移，但会增加内存和计算时间。",
        ),
        "en_US": (
            "Kilosort batch_size",
            "Samples per batch. At 30 kHz, 60000 equals 2 seconds. Low-channel "
            "recordings may need longer batches for drift estimation at higher memory cost.",
        ),
    },
    "sorting.nblocks": {
        "zh_CN": (
            "Kilosort nblocks",
            "漂移校正的探针分区数。0 表示关闭，1 表示整根探针刚性校正，较大的数值用于"
            "深度相关的非刚性漂移。稀疏或少于约 64 通道时通常应为 0。",
        ),
        "en_US": (
            "Kilosort nblocks",
            "Number of probe sections for drift correction. 0 disables correction, "
            "1 applies rigid correction, and larger values model depth-dependent drift. "
            "Sparse or roughly <=64-channel probes usually use 0.",
        ),
    },
    "sorting.thresholds": {
        "zh_CN": (
            "检测阈值",
            "Th_universal 和 Th_learned 越低通常检测到的 spike 越多，同时噪声风险也"
            "增加。应一次只调整 1–2，并比较 unit 数、污染率和时间稳定性。",
        ),
        "en_US": (
            "Detection thresholds",
            "Lower Th_universal and Th_learned generally detect more spikes but increase "
            "noise risk. Adjust by 1-2 and compare unit count, contamination, and stability.",
        ),
    },
    "sorting.ms5_scheme": {
        "zh_CN": (
            "MountainSort5 方案",
            "Scheme 1 把记录载入内存，适合快速测试；Scheme 2 用训练片段建立分类器，"
            "是常规默认；Scheme 3 按块运行 Scheme 2 并跨块关联 Unit，面向长记录和"
            "波形漂移。方案改变实际算法路径。",
        ),
        "en_US": (
            "MountainSort5 scheme",
            "Scheme 1 loads the recording for quick tests; Scheme 2 trains classifiers "
            "on a subset and is the standard default; Scheme 3 processes blocks and "
            "associates units across them for long, drifting recordings.",
        ),
    },
    "sorting.ms5_threshold": {
        "zh_CN": (
            "MountainSort5 检测阈值",
            "以噪声尺度为基准的 spike 检测阈值，默认 5.5。降低通常增加候选 spike "
            "与误检，升高通常增加漏检；应结合波形、事件率和真值/跨 sorter 比较检查。",
        ),
        "en_US": (
            "MountainSort5 detection threshold",
            "Spike threshold relative to the noise scale; default 5.5. Lower values "
            "usually increase candidates and false detections, while higher values "
            "increase misses. Check waveforms, rates, and validation evidence.",
        ),
    },
    "sorting.ms5_training": {
        "zh_CN": (
            "MountainSort5 训练时长",
            "Scheme 2 第一阶段用于无监督聚类和分类器训练的记录时长。更长可覆盖更多"
            "状态但增加耗时；如果记录更短，适配器会由算法按可用范围处理。",
        ),
        "en_US": (
            "MountainSort5 training duration",
            "Recording duration used by Scheme 2 phase 1 for clustering and classifier "
            "training. Longer windows cover more states at greater computational cost.",
        ),
    },
    "sorting.view": {
        "zh_CN": (
            "Sorting 诊断视图",
            "在统一结果比较、ground truth 验证、流程日志、深度-时间漂移图、振幅"
            "稳定性、模板波形、相似度矩阵和输出文件之间切换。它们读取真实 sorter "
            "输出，不重新 sorting。",
        ),
        "en_US": (
            "Sorting diagnostic view",
            "Switch among normalized comparison, ground-truth validation, pipeline log, "
            "depth-time drift, amplitude stability, templates, similarity matrix, and "
            "exported files. Views read real sorter output.",
        ),
    },
}


PAGE_CONTROLS = {
    "import": [
        (
            "数据来源 / Source",
            "决定读取适配器；选择错误不会改变文件，但会导致校验失败。",
        ),
        ("项目名称 / Project name", "用于项目文件夹和清单显示，不改变原始文件名。"),
        ("采样率 / Sampling rate", "把采样点转换成秒；错误值会使全部时间分析失真。"),
        ("通道数 / Channel count", "决定二进制重排；错误值常表现为重复或斜纹波形。"),
        ("dtype 与 μV/bit", "决定每个样本的字节解释和电压换算。"),
    ],
    "qc": [
        ("通道 RMS", "单击柱子查看通道号和 RMS；异常通道以警示色显示。"),
        ("50 Hz 比值", "比较工频功率与邻近频率背景，不等同于绝对噪声振幅。"),
        ("坏通道建议", "只是候选列表；应回到原始波形核实后再排除。"),
        ("时间/通道/增益控件", "用于定位异常，不修改原始记录。"),
    ],
    "preprocess": [
        ("处理前/后波形", "使用同一时间窗比较滤波和 common median reference 的影响。"),
        ("预览节点", "只计算短片段，不写回原始记录。"),
        ("缩放工具", "放大检查波形极性、边缘效应和伪迹残留。"),
    ],
    "sorting": [
        ("Sorter 表", "显示全部候选工具、安装状态、硬件和适用记录；单击选择。"),
        ("参数预设", "把电极类型映射到一组可审计参数，仍允许逐项修改。"),
        ("运行当前节点", "使用当前选择真实执行 sorter，并保存完整日志和输出目录。"),
        ("诊断视图", "检查 drift、振幅、模板、相似度、污染率和导出文件。"),
    ],
    "unit_qc": [
        ("Unit 表", "每行是一个候选 unit；单击图中点或表格查看指标。"),
        ("ISI violation", "衡量短于不应期的间隔比例；阈值必须在项目中预先定义。"),
        ("SNR 与波形", "需要结合空间局限性、稳定性和原始波形，不能单独决定 good。"),
    ],
    "sync": [
        ("事件数量", "确认行为、TTL 和神经数据中的事件能一一对应。"),
        ("时间残差", "显示配对事件的偏差；随时间变化提示时钟漂移。"),
        ("trial 表", "保存条件、事件时间和排除标记，供后续分析使用。"),
    ],
    "behavior": [
        ("条件计数", "确认类别是否平衡以及每类 trial 是否足够。"),
        ("反应时", "定位缺失、极端值和条件相关变化。"),
        ("心理测量曲线", "每个点对应一个刺激水平，应同时检查该点样本量。"),
    ],
    "analysis": [
        ("Unit 选择", "选择一个 unit 后，Raster、PSTH 和摘要同步更新。"),
        ("Raster", "每行一个 trial，每个短线一个 spike，保留试次差异。"),
        ("PSTH", "对 spike 分箱并跨 trial 平均；分箱宽度影响平滑程度。"),
        ("Spike train 统计", "CV2、Lv、Fano、CCH、STTC 和距离回答不同的变异性、相关性或相似性问题。"),
        ("LFP", "PSD、coherence、相位延迟和时频图使用带单位的 Neo 信号与 Elephant/SciPy 计算。"),
        ("Spike-field", "相位锁定必须说明参考频段、相位定义、spike 数和 surrogate 方法。"),
        ("呼吸案例", "只在 NeuroFlow 模拟数据上验证论文方法结构，不复制原图或数值结论。"),
    ],
    "statistics": [
        ("视图选择", "在效应、多重比较、分布假设和混合模型诊断间切换。"),
        ("表格", "提供统计量、p 值、校正值、效应量和置信区间。"),
        ("样本单位", "必须区分 trial、unit、session 和动物，避免伪重复。"),
    ],
    "decoding": [
        ("任务与模型", "选择分类或回归算法；选择后只有点击运行才会训练。"),
        ("交叉验证", "每折只用训练数据拟合预处理，测试折用于独立评价。"),
        ("置换基线", "打乱标签形成零假设分布，用于判断模型是否超过偶然水平。"),
        ("PCA/聚类", "用于探索群体结构，不自动提供科学因果解释。"),
    ],
    "export": [
        ("图形设置", "修改当前图的标题、坐标、范围和网格。"),
        ("SVG/PDF/PNG", "SVG/PDF 保留矢量元素；PNG 用于快速预览。"),
        ("CSV 与 Methods", "同时导出绘图数据、统计表、参数、版本和方法草稿。"),
        ("项目清单", "记录来源和执行状态，使结果能回到对应输入与参数。"),
    ],
}

PAGE_CONTROLS_EN = {
    "import": [
        (
            "Data source",
            "Selects the reader adapter. A wrong selection does not alter the file, but validation will fail.",
        ),
        (
            "Project name",
            "Names the project folder and manifest; the original file name is unchanged.",
        ),
        (
            "Sampling rate",
            "Converts samples to seconds. An incorrect value invalidates every time-based result.",
        ),
        (
            "Channel count",
            "Controls binary reshaping. A wrong value commonly creates repeated or diagonal trace patterns.",
        ),
        (
            "dtype and µV/bit",
            "Define byte interpretation and conversion from stored values to voltage.",
        ),
    ],
    "qc": [
        (
            "Channel RMS",
            "Click a bar to inspect channel number and RMS; flagged channels use the warning color.",
        ),
        (
            "50 Hz ratio",
            "Compares line-frequency power with neighboring background frequencies; it is not an absolute noise amplitude.",
        ),
        (
            "Bad-channel candidates",
            "These are suggestions only. Verify them against raw traces before exclusion.",
        ),
        (
            "Time/channel/gain controls",
            "Locate suspicious segments without changing the recording.",
        ),
    ],
    "preprocess": [
        (
            "Before/after traces",
            "Compare filtering and common-median referencing on the same time segment.",
        ),
        (
            "Preview stage",
            "Computes a short preview only and never writes over the source recording.",
        ),
        (
            "Zoom tools",
            "Inspect polarity, edge effects, clipping, and residual artifacts at sample-level detail.",
        ),
    ],
    "sorting": [
        (
            "Sorter table",
            "Lists every candidate, installation status, hardware needs, and suited recording types. Click a row to select.",
        ),
        (
            "Parameter preset",
            "Maps recording type to auditable defaults while keeping every value editable.",
        ),
        (
            "Run current stage",
            "Runs the selected sorter with current parameters and preserves its full log and result directory.",
        ),
        (
            "Diagnostic view",
            "Inspect drift, amplitude stability, templates, similarity, contamination, and exported files.",
        ),
    ],
    "unit_qc": [
        (
            "Unit table",
            "Each row is one candidate unit. Click data points or rows to inspect its metrics.",
        ),
        (
            "ISI violation",
            "Measures short refractory-period intervals; the acceptance threshold must be defined by the project.",
        ),
        (
            "SNR and waveform",
            "Interpret together with spatial localization, stability, and raw traces; no single metric proves a good unit.",
        ),
    ],
    "sync": [
        (
            "Event count",
            "Confirm that behavior, TTL, and neural events can be matched one-to-one.",
        ),
        (
            "Timing residual",
            "Shows paired-event error; a systematic change over time suggests clock drift.",
        ),
        (
            "Trial table",
            "Stores conditions, event times, and exclusion flags for downstream analyses.",
        ),
    ],
    "behavior": [
        (
            "Condition counts",
            "Check class balance and whether every condition has enough trials.",
        ),
        (
            "Reaction time",
            "Locate missing values, extremes, and condition-dependent changes.",
        ),
        (
            "Psychometric curve",
            "Each point represents one stimulus level and should be interpreted with its trial count.",
        ),
    ],
    "analysis": [
        (
            "Unit selection",
            "Selecting a unit updates its raster, PSTH, and summary together.",
        ),
        (
            "Raster",
            "Each row is one trial and each tick one spike, preserving trial-to-trial variability.",
        ),
        (
            "PSTH",
            "Bins spikes and averages across trials; bin width controls temporal smoothing.",
        ),
        (
            "Spike-train statistics",
            "CV2, Lv, Fano, CCH, STTC, and distances address different variability, correlation, or similarity questions.",
        ),
        (
            "LFP",
            "PSD, coherence, phase lag, and time-frequency maps use unit-aware Neo signals with Elephant/SciPy.",
        ),
        (
            "Spike-field",
            "Phase locking must report the reference band, phase definition, spike count, and surrogate method.",
        ),
        (
            "Respiration case",
            "Validates a paper-derived method structure on NeuroFlow simulation data without copying figures or numerical claims.",
        ),
    ],
    "statistics": [
        (
            "Diagnostic view",
            "Switch among effects, multiplicity, distribution assumptions, and mixed-model diagnostics.",
        ),
        (
            "Results table",
            "Reports statistics, raw and corrected p values, effect sizes, and confidence intervals.",
        ),
        (
            "Sampling unit",
            "Distinguish trials, units, sessions, and animals to avoid pseudoreplication.",
        ),
    ],
    "decoding": [
        (
            "Task and model",
            "Choose classification or regression. Training starts only after Run is pressed.",
        ),
        (
            "Cross-validation",
            "Fits preprocessing inside each training fold and reserves test folds for independent evaluation.",
        ),
        (
            "Permutation baseline",
            "Shuffles labels to estimate performance under the null hypothesis.",
        ),
        (
            "PCA/clustering",
            "Explores population structure; it does not establish a biological causal explanation.",
        ),
    ],
    "export": [
        (
            "Figure settings",
            "Edit the current figure title, axis names, limits, and grid.",
        ),
        (
            "SVG/PDF/PNG",
            "SVG and PDF retain vector elements; PNG is suited to quick previews.",
        ),
        (
            "CSV and Methods",
            "Export plotting data, statistical tables, parameters, versions, and a methods draft together.",
        ),
        (
            "Project manifest",
            "Links every result back to source data, parameters, and execution state.",
        ),
    ],
}


def control_help(key: str, language: str) -> tuple[str, str]:
    values = CONTROL_HELP.get(key)
    if values is None:
        return (
            ("控件说明", "此控件尚未登记具体说明。")
            if language == "zh_CN"
            else (
                "Control help",
                "No detailed help has been registered for this control.",
            )
        )
    return values.get(language, values["zh_CN"])


def page_controls(key: str, language: str) -> list[tuple[str, str]]:
    if language == "en_US":
        return PAGE_CONTROLS_EN.get(key, [])
    return PAGE_CONTROLS.get(key, [])
