from __future__ import annotations

from typing import Any

DEFAULT_TRANSLATIONS = {
    "模拟项目 30,000 Hz；设备文件读取元数据": "Simulation: 30,000 Hz; device files: read from metadata",
    "模拟项目由电极模板决定": "Defined by the simulation electrode template",
    "通用导入 0.195；设备导入读取或标准化": "Generic import: 0.195; device import: read or normalize",
    "关闭：只读索引": "Off: read-only link",
    "50 Hz（中国与多数地区）": "50 Hz in China and most regions",
    "默认关闭": "Off",
    "从项目结构读取": "Read from the project structure",
    "60,000（30 kHz 时 2 s）": "60,000 (2 s at 30 kHz)",
    "1（刚性漂移）": "1 (rigid drift)",
    "Kilosort4 当前默认": "Current Kilosort4 default",
    "整段记录": "Full recording",
    "Kilosort4 默认": "Kilosort4 default",
    "仅报告，不默认剔除": "Report only; no automatic exclusion",
    "仅报告": "Report only",
    "全记录时间线": "Full-session timeline",
    "不自动设为真值": "Not treated as ground truth",
    "按顺序一一配对": "Pair one-to-one in order",
    "报告实际值，不自动隐藏": "Report the observed value without hiding it",
    "仅在未提供 TTL 时启用并警告": "Enabled with a warning only when TTLs are absent",
    "仅警告，不自动剔除": "Warning only; no automatic exclusion",
    "不默认删除": "No deletion by default",
    "stimulus_onset（取决于事件表）": "stimulus_onset (depends on the event table)",
    "-1 到 +2 s": "-1 to +2 s",
    "默认最小或关闭": "Minimal or off",
    "200（演示）": "200 (demonstration)",
    "必须由用户确认": "Must be confirmed by the user",
    "根据设计": "Defined by the study design",
    "0–0.5 s（依任务而定）": "0–0.5 s (task-dependent)",
    "5-fold stratified 或 grouped": "5-fold stratified or grouped",
    "线性/SVM 模型使用 StandardScaler": "StandardScaler for linear/SVM models",
    "balanced（不平衡时）": "balanced (for imbalanced classes)",
    "按当前图": "Use the current figure",
    "NeuroFlow 标准主题": "NeuroFlow standard theme",
    "取决于导入选择": "Defined by the import choice",
}


def _operation(
    name: str,
    name_en: str,
    action: str,
    action_en: str,
    purpose: str,
    purpose_en: str,
    result: str,
    result_en: str,
) -> dict[str, str]:
    return {
        "name": name,
        "name_en": name_en,
        "action": action,
        "action_en": action_en,
        "purpose": purpose,
        "purpose_en": purpose_en,
        "result": result,
        "result_en": result_en,
    }


def _parameter(
    name: str,
    meaning: str,
    meaning_en: str,
    default: str,
    recommended: str,
    recommended_en: str,
    effect: str,
    effect_en: str,
) -> dict[str, str]:
    localized_name = name
    english_name = name
    if " / " in name:
        left, right = name.split(" / ", 1)
        if any("\u4e00" <= character <= "\u9fff" for character in right):
            localized_name = f"{right}（{left}）"
            english_name = left
    return {
        "name": localized_name,
        "name_en": english_name,
        "meaning": meaning,
        "meaning_en": meaning_en,
        "default": default,
        "default_en": DEFAULT_TRANSLATIONS.get(default, default),
        "recommended": recommended,
        "recommended_en": recommended_en,
        "effect": effect,
        "effect_en": effect_en,
    }


TUTORIAL_DETAILS: dict[str, dict[str, Any]] = {
    "import": {
        "narrative": (
            "这一页不是简单的“选文件”。NeuroFlow 必须先知道每个采样值怎样存储、"
            "多少个值组成一个时间点、探针通道怎样排列，以及行为事件使用哪一台设备的"
            "时钟。只有这些结构被确认，后面的滤波、sorting 和事件对齐才有正确的物理"
            "单位。导入过程保持原始数据只读，项目只保存索引、缓存和派生结果。"
        ),
        "narrative_en": (
            "This page does more than select a file. NeuroFlow must know how each "
            "sample is stored, how many values form one time point, how probe "
            "contacts are arranged, and which device clock timestamps behavior. "
            "Those facts give filtering, sorting, and event alignment their correct "
            "physical units. Import keeps the source read-only and stores only "
            "links, caches, and derived results in the project."
        ),
        "before": (
            "准备记录系统说明、采样率、总通道数、数据类型、增益或 μV/bit、探针几何，"
            "以及可选的事件 CSV。若是通用二进制，必须从采集软件配置中核对，而不是凭"
            "波形猜参数。"
        ),
        "before_en": (
            "Have the acquisition notes, sampling rate, total channel count, dtype, "
            "gain or µV/bit, probe geometry, and optional event CSV ready. For a "
            "generic binary file, copy values from the acquisition configuration "
            "rather than guessing from the traces."
        ),
        "operations": [
            _operation(
                "创建空项目",
                "Create an empty project",
                "先指定项目名称和保存目录，再从项目内导入数据。",
                "Choose a project name and location, then import data inside it.",
                "把原始数据与分析产物分开，并建立后续恢复入口。",
                "Separates source data from analysis products and creates a restore point.",
                "生成 neuroflow_project.json、derived、results 和 exports 目录。",
                "Creates neuroflow_project.json plus derived, results, and exports folders.",
            ),
            _operation(
                "导入通用二进制",
                "Import generic binary",
                "选择 .bin/.dat/.raw，填写采样率、通道数、dtype 和 μV/bit。",
                "Select .bin/.dat/.raw and enter rate, channels, dtype, and µV/bit.",
                "读取没有自描述元数据的交错通道记录。",
                "Reads interleaved recordings without self-describing metadata.",
                "验证文件大小能否被“通道数 × 每样本字节数”整除，并显示波形。",
                "Validates file size against channels × bytes per sample and displays traces.",
            ),
            _operation(
                "导入记录系统文件",
                "Import acquisition-system data",
                "选择 Intan、Open Ephys、SpikeGLX、Blackrock、Plexon、TDT 或 NWB。",
                "Choose Intan, Open Ephys, SpikeGLX, Blackrock, Plexon, TDT, or NWB.",
                "利用 SpikeInterface extractor 读取设备元数据并建立统一缓存。",
                "Uses a SpikeInterface extractor to read metadata and build a common cache.",
                "项目中保存标准 int16 缓存，源文件保持不变。",
                "Stores a normalized int16 cache while leaving source files unchanged.",
            ),
            _operation(
                "从已有 sorting 继续",
                "Resume from existing sorting",
                "选择 Kilosort/Phy、IBL ALF 或含 Units 的 NWB。",
                "Select Kilosort/Phy, IBL ALF, or an NWB file with Units.",
                "跳过无法重复的原始处理阶段，直接进入 Unit 和下游分析。",
                "Skips unavailable raw stages and continues with units and downstream analyses.",
                "统一得到以秒表示的 spike times、unit ID 和来源记录。",
                "Produces normalized spike times in seconds, unit IDs, and provenance.",
            ),
        ],
        "parameters": [
            _parameter(
                "Sampling rate / 采样率",
                "每秒采样点数，用于样本索引与秒之间的换算。",
                "Samples per second; converts sample indices to seconds.",
                "模拟项目 30,000 Hz；设备文件读取元数据",
                "必须使用采集系统记录值；常见细胞外 spike 记录为 20–30 kHz。",
                "Use the acquisition value exactly; extracellular spike recordings commonly use 20–30 kHz.",
                "填小会把时间拉长、频率压低；填大会把时间压短、频率抬高。",
                "A low value stretches time and lowers frequencies; a high value compresses time and raises frequencies.",
            ),
            _parameter(
                "Channel count / 总通道数",
                "二进制每个时间点包含的全部通道，包括文件中的辅助通道。",
                "All channels stored per time point, including auxiliary channels in the file.",
                "模拟项目由电极模板决定",
                "按文件实际写入通道数填写，不等同于用于 sorting 的电生理通道数。",
                "Use the number physically written to the file, not merely the channels selected for sorting.",
                "错误值会重排整个文件，常出现重复、错位或斜纹波形。",
                "A wrong value reshapes the file and often creates repeated, shifted, or diagonal patterns.",
            ),
            _parameter(
                "dtype / 数据类型",
                "每个样本在磁盘上的存储类型。",
                "Storage type of each sample on disk.",
                "int16",
                "优先从设备元数据或导出设置读取；不要把 float32 文件当作 int16。",
                "Read it from device metadata or export settings; never interpret float32 as int16.",
                "错误 dtype 会改变帧长度和数值解释，可能仍能打开但波形完全错误。",
                "A wrong dtype changes frame length and numeric interpretation; the file may open with invalid traces.",
            ),
            _parameter(
                "µV / bit",
                "一个整数 ADC 步长对应的微伏数。",
                "Microvolts represented by one integer ADC step.",
                "通用导入 0.195；设备导入读取或标准化",
                "使用设备增益换算；若不确定，先保留原始计数并标记单位未知。",
                "Use the acquisition gain; if unknown, keep ADC counts and mark units as unknown.",
                "只影响振幅单位和依赖振幅的阈值，不改变 spike 的样本位置。",
                "Affects amplitude units and amplitude-dependent thresholds, not spike sample locations.",
            ),
            _parameter(
                "Copy source / 复制源文件",
                "决定项目保存只读路径还是把原始二进制复制到项目。",
                "Chooses a read-only link or a copied raw binary inside the project.",
                "关闭：只读索引",
                "数据位置稳定时用索引；需要移动或长期归档项目时开启复制。",
                "Use a link for stable storage; copy when the project must move or be archived independently.",
                "复制提高可移植性但占用额外磁盘；索引节省空间但源路径失效后无法重读。",
                "Copying improves portability at a storage cost; links save space but fail if the source moves.",
            ),
        ],
        "recommended": [
            "先创建项目，再选择与你手中真实文件相符的入口。",
            "导入后只查看 50–100 ms 波形，确认通道数量、振幅单位和时间长度。",
            "保存项目；重新打开 neuroflow_project.json 应回到上次页面和工作流状态。",
        ],
        "recommended_en": [
            "Create a project first, then choose the entry that matches the files you actually have.",
            "Inspect 50–100 ms of traces and verify channel count, amplitude units, and duration.",
            "Save the project; reopening neuroflow_project.json should restore the page and workflow state.",
        ],
        "pitfalls": [
            "把 384 个电生理通道误当作文件总通道数，而文件实际还含同步通道。",
            "移动外部原始文件后仍期待只读索引自动找到新位置。",
            "IBL ALF 或 Units-only NWB 不含原始电压，不能回到 sorting 之前。",
        ],
        "pitfalls_en": [
            "Using 384 ephys channels as the file total when a sync channel is also stored.",
            "Moving an external source and expecting a read-only link to discover its new location.",
            "Expecting IBL ALF or Units-only NWB to provide raw voltage for re-sorting.",
        ],
        "next": "确认结构后进入原始质控；如果只有处理后 spike，则直接进入 Unit 质控。",
        "next_en": "After confirming structure, continue to Raw QC; processed spikes begin at Unit QC.",
    },
    "qc": {
        "narrative": (
            "质控的目标不是自动删除通道，而是建立证据：异常发生在哪些通道、哪些时间、"
            "哪些频率，以及是否可能影响重参考和 spike 检测。先在整段记录上定位问题，"
            "再放大到原始波形核实，最后才给出坏通道候选。"
        ),
        "narrative_en": (
            "QC does not automatically delete channels. It builds evidence about "
            "where an anomaly occurs in channel, time, and frequency and whether it "
            "can affect referencing or spike detection. Locate problems globally, "
            "verify them in zoomed traces, and only then label candidate bad channels."
        ),
        "before": "确保数据结构页的采样率、通道数、单位和记录时长已经核对。",
        "before_en": "Verify sampling rate, channel count, units, and duration on the Data page.",
        "operations": [
            _operation(
                "多通道原始波形",
                "Multichannel raw traces",
                "用时间窗、起点、通道范围和显示增益逐段浏览。",
                "Browse with time window, start time, channel range, and display gain.",
                "识别饱和、跳变、运动伪迹、死通道和共同噪声。",
                "Find clipping, jumps, motion artifacts, dead channels, and common noise.",
                "得到可缩放的真实电压片段和当前窗口 RMS。",
                "Produces zoomable voltage snippets and RMS for the current window.",
            ),
            _operation(
                "质控指标总览",
                "QC metric summary",
                "运行该子分析，查看每通道 RMS、峰峰值、饱和比例和工频比值。",
                "Run the sub-analysis and inspect RMS, peak-to-peak, clipping, and line-noise ratios.",
                "用多个指标共同筛选，而不是依赖单一阈值。",
                "Screens channels using several metrics rather than one threshold.",
                "生成候选坏通道表；不会自动排除。",
                "Creates a candidate bad-channel table without automatic exclusion.",
            ),
            _operation(
                "通道 × 频率功率",
                "Channel-by-frequency power",
                "查看所有通道的功率谱热图并缩放可疑频带。",
                "Inspect the channel-by-frequency power map and zoom suspicious bands.",
                "区分宽带噪声、50/60 Hz 工频和局部通道异常。",
                "Distinguishes broadband noise, 50/60 Hz line noise, and local channel problems.",
                "得到各通道频谱证据和工频峰值。",
                "Produces channel spectra and line-frequency evidence.",
            ),
            _operation(
                "质量时间线",
                "Quality timeline",
                "按时间块计算振幅、噪声和饱和指标。",
                "Compute amplitude, noise, and clipping metrics in time blocks.",
                "发现只在部分记录中出现的掉线、漂移或伪迹。",
                "Finds dropouts, drift, or artifacts limited to part of the session.",
                "得到异常时间段，供预处理中的排除或修复使用。",
                "Produces suspect intervals for exclusion or repair during preprocessing.",
            ),
        ],
        "parameters": [
            _parameter(
                "Time start / 起始时间",
                "当前预览窗口从记录的哪一秒开始。",
                "Start of the displayed recording window.",
                "0 s",
                "先看开头，再抽查中段、结尾和任务关键事件附近。",
                "Inspect the beginning, middle, end, and intervals around key task events.",
                "只改变显示和局部指标，不裁剪原始数据。",
                "Changes the view and local metrics without cropping the source.",
            ),
            _parameter(
                "Window / 时间窗",
                "一次显示多少毫秒或秒。",
                "Duration displayed at once.",
                "60 ms",
                "spike 波形用 20–100 ms；慢伪迹和节律可用 1–10 s。",
                "Use 20–100 ms for spikes and 1–10 s for slow artifacts or rhythms.",
                "短窗看波形细节，长窗看趋势，但过长会压缩尖峰。",
                "Short windows reveal waveforms; long windows reveal trends but compress spikes.",
            ),
            _parameter(
                "Channel range / 通道范围",
                "同时绘制的起始通道与数量。",
                "First channel and number shown together.",
                "Ch 0–11",
                "密集探针每次看 8–16 通道，并沿深度移动。",
                "Inspect 8–16 channels at a time on dense probes and move along depth.",
                "通道过多会降低单通道可读性；过少可能看不到空间共同模式。",
                "Too many channels reduce readability; too few can hide spatially shared patterns.",
            ),
            _parameter(
                "Display gain / 显示增益",
                "仅控制各通道在图中的垂直放大倍数。",
                "Vertical display multiplier only.",
                "1.0×",
                "从 1.0× 开始，波形重叠时调低，振幅过小时调高。",
                "Start at 1.0×, decrease for overlap, and increase for small traces.",
                "不改变数据和 QC 数值，只改变可视化。",
                "Does not alter data or QC values; it only changes the view.",
            ),
            _parameter(
                "Line frequency / 工频",
                "用于计算窄带工频功率的中心频率。",
                "Center frequency for narrowband mains-power measurement.",
                "50 Hz（中国与多数地区）",
                "按实验所在地选择 50 或 60 Hz，并同时查看谐波。",
                "Choose 50 or 60 Hz for the recording location and inspect harmonics.",
                "选错频率会漏报工频，但不会改变原始信号。",
                "The wrong choice misses mains noise but does not alter the source.",
            ),
        ],
        "recommended": [
            "先运行总览和时间线，再用原始波形、频谱对每个候选异常交叉验证。",
            "坏通道标签必须记录证据和人工决定，不在质控页直接删除。",
            "质控结论保存后再进入预处理，避免重参考被异常通道污染。",
        ],
        "recommended_en": [
            "Run summary and timeline first, then verify every candidate in traces and spectra.",
            "Record evidence and the manual decision; do not delete channels directly on the QC page.",
            "Save QC decisions before preprocessing so bad channels do not contaminate referencing.",
        ],
        "pitfalls": [
            "把高放电通道误判为高噪声通道。",
            "只看记录开头几十毫秒就宣布整段记录质量良好。",
            "看到 50 Hz 峰就直接 notch，而不检查接地、参考和谐波。",
        ],
        "pitfalls_en": [
            "Confusing a high-firing channel with a noisy channel.",
            "Declaring the whole session good after inspecting only the first milliseconds.",
            "Applying a notch immediately without checking grounding, reference, and harmonics.",
        ],
        "next": "把确认的坏通道和异常时间段带入预处理，分别建立 AP 与 LFP 分支。",
        "next_en": "Carry confirmed bad channels and artifact intervals into separate AP and LFP preprocessing branches.",
    },
    "preprocess": {
        "narrative": (
            "预处理不是“越多越干净”。每个操作都改变信号，因此必须说明目标、顺序和"
            "是否会在 sorter 内再次执行。NeuroFlow 默认先做短片段预览，让用户比较"
            "处理前后波形和频谱；确认后才把参数写入工作流。"
        ),
        "narrative_en": (
            "More preprocessing is not automatically better. Every operation changes "
            "the signal, so its purpose, order, and duplication inside the sorter must "
            "be explicit. NeuroFlow previews a short segment first and compares traces "
            "and spectra before parameters are committed to the workflow."
        ),
        "before": "先完成坏通道确认；明确当前目标是 AP/spike sorting、LFP，还是两者。",
        "before_en": "Confirm bad channels and decide whether the target is AP/sorting, LFP, or both.",
        "operations": [
            _operation(
                "AP / sorting 预览",
                "AP / sorting preview",
                "选择高通/带通、参考方式和预览片段。",
                "Choose high-pass/band-pass, reference, and preview segment.",
                "突出快速动作电位并评估 sorter 输入。",
                "Emphasizes fast action potentials and evaluates sorter input.",
                "显示处理前后波形、频谱和 RMS 变化。",
                "Shows before/after traces, spectra, and RMS changes.",
            ),
            _operation(
                "LFP 分支预览",
                "LFP branch preview",
                "选择低通、降采样率和工频处理。",
                "Choose low-pass, downsampling, and line-noise handling.",
                "保留低频群体活动并降低后续计算量。",
                "Preserves low-frequency population activity and reduces later computation.",
                "生成独立 LFP 处理链，不覆盖 AP 分支。",
                "Creates an independent LFP chain without overwriting the AP branch.",
            ),
            _operation(
                "重参考比较",
                "Reference comparison",
                "比较 none、common median 和 common average。",
                "Compare none, common median, and common average.",
                "减少通道间共同噪声，同时检查是否传播坏通道伪迹。",
                "Reduces common noise while checking whether bad-channel artifacts spread.",
                "显示参考前后共同成分和单通道波形。",
                "Displays common components and channel traces before and after referencing.",
            ),
            _operation(
                "写入处理链",
                "Commit processing chain",
                "确认预览后保存操作顺序和参数。",
                "Save operation order and parameters after reviewing the preview.",
                "使 sorting、LFP 和复现导出使用同一可追溯配置。",
                "Makes sorting, LFP, and reproducibility exports use the same traceable configuration.",
                "项目记录处理链；原始文件仍保持只读。",
                "Stores the processing chain while the source remains read-only.",
            ),
        ],
        "parameters": [
            _parameter(
                "AP band / AP 频段",
                "提供给 spike 检测或预览的通带。",
                "Passband used for spike detection or preview.",
                "300–6000 Hz",
                "先使用 sorter 或领域常见默认；根据采样率和频谱证据调整。",
                "Start with sorter/domain defaults and adjust only from sampling rate and spectral evidence.",
                "高通太高会削弱宽波形；太低会保留 LFP 漂移。低通不能超过 Nyquist。",
                "A high lower cutoff suppresses broad spikes; a low one retains LFP drift. The upper cutoff must stay below Nyquist.",
            ),
            _parameter(
                "LFP low-pass / LFP 低通",
                "保留的最高 LFP 频率。",
                "Highest retained LFP frequency.",
                "300 Hz",
                "若只分析 <100 Hz，可设 150–250 Hz；研究高频振荡需提高并保留足够采样率。",
                "Use 150–250 Hz for analyses below 100 Hz; retain a higher cutoff and sampling rate for high-frequency oscillations.",
                "截止频率越低，尖锐瞬态越被平滑；过高会把 spike 泄漏带入 LFP。",
                "Lower cutoffs smooth transients; overly high cutoffs allow spike leakage into LFP.",
            ),
            _parameter(
                "LFP sampling rate / 降采样率",
                "滤波后 LFP 每秒保存的样本数。",
                "Samples per second retained after LFP filtering.",
                "1,000 Hz",
                "至少为目标最高频率的 2 倍，实际通常保留 4–10 倍余量。",
                "Keep at least twice the highest target frequency; 4–10× margin is common.",
                "过低会混叠或失去相位精度；过高增加内存和计算。",
                "Too low causes aliasing or poor phase precision; too high increases memory and computation.",
            ),
            _parameter(
                "Reference / 参考方式",
                "从每个通道减去共同参考估计。",
                "Common reference estimate subtracted from each channel.",
                "Common median",
                "密集多通道记录可从 median 开始；稀疏 tetrode/微丝需结合分组和参考电极。",
                "Start with median for dense recordings; use probe groups and reference design for sparse tetrodes or microwires.",
                "average 更受极端通道影响；median 更稳健，但两者都可能移除真实共同活动。",
                "Average is more sensitive to outliers; median is robust, but both can remove genuine common activity.",
            ),
            _parameter(
                "Notch / 陷波",
                "压制 50/60 Hz 及可选谐波。",
                "Suppresses 50/60 Hz and optional harmonics.",
                "默认关闭",
                "只有质控证据显示窄带污染且无法从硬件修复时开启。",
                "Enable only when QC shows narrowband contamination that cannot be corrected at acquisition.",
                "陷波会改变目标频率附近的振幅和相位，可能影响相位耦合分析。",
                "Notching changes amplitude and phase around the target and can affect coupling analyses.",
            ),
        ],
        "recommended": [
            "AP 和 LFP 建立独立分支，不把同一处理链机械复用。",
            "先预览再确认；图中同时保留原始、处理后和差值/频谱证据。",
            "检查 sorter 是否内部执行滤波、whitening 和 drift correction，避免重复。",
        ],
        "recommended_en": [
            "Create separate AP and LFP branches rather than reusing one recipe.",
            "Preview before committing and retain raw, processed, and difference/spectral evidence.",
            "Check whether the sorter already filters, whitens, or corrects drift to avoid duplication.",
        ],
        "pitfalls": [
            "在外部和 Kilosort 内重复 whitening。",
            "坏通道未排除就做全局参考。",
            "先降采样再低通，造成混叠。",
        ],
        "pitfalls_en": [
            "Whitening both externally and inside Kilosort.",
            "Applying a global reference before excluding bad channels.",
            "Downsampling before low-pass filtering and causing aliasing.",
        ],
        "next": "AP 分支进入 Spike sorting；LFP 分支保留到神经活动分析页。",
        "next_en": "Send the AP branch to Spike sorting and retain the LFP branch for neural analyses.",
    },
    "sorting": {
        "narrative": (
            "Spike sorting 把多通道电压中的候选事件分配给 unit。NeuroFlow 不把不同 "
            "sorter 的原生输出强行抹平：它保留原始文件、参数和日志，同时把共同结果转换"
            "为统一的 unit、spike 秒时间和通道/模板描述，供下游比较。"
        ),
        "narrative_en": (
            "Spike sorting assigns candidate events in multichannel voltage to units. "
            "NeuroFlow preserves each sorter's native files, parameters, and logs while "
            "normalizing shared outputs into units, spike times in seconds, and "
            "channel/template descriptions for downstream comparison."
        ),
        "before": "确认 AP 输入、探针几何、坏通道、可用硬件、输出目录和预计磁盘空间。",
        "before_en": "Confirm AP input, probe geometry, bad channels, hardware, output directory, and free disk space.",
        "operations": [
            _operation(
                "选择 sorter",
                "Select a sorter",
                "在表中选择 Kilosort4、MountainSort5 或其他已安装后端。",
                "Choose Kilosort4, MountainSort5, or another installed backend.",
                "按探针密度、硬件和研究需求选择算法，而不是只按“能运行”。",
                "Chooses an algorithm by probe density, hardware, and scientific need, not only availability.",
                "参数区切换到该 sorter 的真实配置，未运行时显示输入预览。",
                "Loads that sorter's real settings and shows input preview before a run.",
            ),
            _operation(
                "运行所选 sorter",
                "Run selected sorter",
                "确认弹窗中的数据、sorter、参数和运行位置。",
                "Confirm data, sorter, parameters, and execution location in the dialog.",
                "防止把耗时任务误运行在错误数据或错误配置上。",
                "Prevents expensive runs on the wrong data or configuration.",
                "保存原生输出、统一结果、版本、参数、日志和诊断图。",
                "Saves native output, normalized results, versions, settings, logs, and diagnostics.",
            ),
            _operation(
                "查看运行诊断",
                "Inspect run diagnostics",
                "切换 drift、spike 深度-时间、振幅、模板、相似度和运行日志。",
                "Switch among drift, spike depth-time, amplitudes, templates, similarity, and logs.",
                "判断算法是否在整段记录和整个探针上稳定工作。",
                "Assesses stability across time and probe depth.",
                "得到进入 Unit QC 前的 sorting 证据。",
                "Produces sorting evidence required before Unit QC.",
            ),
            _operation(
                "比较 sorter",
                "Compare sorters",
                "激活不同结果并运行 unit 匹配与一致度比较。",
                "Activate different results and run unit matching and agreement comparison.",
                "识别共识、拆分、合并和仅单一算法发现的 unit。",
                "Identifies consensus units, splits, merges, and sorter-specific units.",
                "真实数据报告 agreement；有 ground truth 的模拟数据才报告 accuracy。",
                "Reports agreement on real data and accuracy only when simulation ground truth exists.",
            ),
        ],
        "parameters": [
            _parameter(
                "Sorter",
                "实际执行的 spike sorting 后端。",
                "Spike-sorting backend that will actually run.",
                "Kilosort4",
                "高密度 Neuropixels 优先评估 Kilosort4；稀疏/tetrode 可比较 CPU sorter。",
                "Evaluate Kilosort4 first for dense Neuropixels; compare CPU sorters for sparse/tetrode recordings.",
                "不同 sorter 的预处理、检测、聚类和资源需求不同，结果不可视为同一算法的参数变体。",
                "Sorters differ in preprocessing, detection, clustering, and resources; they are not interchangeable parameter presets.",
            ),
            _parameter(
                "n_chan_bin",
                "Kilosort 二进制文件中的总通道数，包括未用于 sorting 的通道。",
                "Total channels in the Kilosort binary, including channels not used for sorting.",
                "从项目结构读取",
                "必须与文件物理布局一致；Neuropixels 1.0 常见文件总数为 385。",
                "Must match the physical file layout; Neuropixels 1.0 files commonly contain 385 channels.",
                "错误值会产生重复斜纹或错位热图，应在运行前立即停止。",
                "A wrong value creates diagonal/repeated heatmaps and should stop the run immediately.",
            ),
            _parameter(
                "batch_size",
                "Kilosort 每个批次处理的样本数。",
                "Samples processed in each Kilosort batch.",
                "60,000（30 kHz 时 2 s）",
                "先用默认；≤64 通道且漂移估计不稳时可增加批次包含的时间。",
                "Start with the default; for ≤64 channels, a longer batch can improve drift estimation.",
                "更大批次需要更多显存/内存；过短批次用于漂移估计的 spike 更少。",
                "Larger batches need more memory; short batches contain fewer spikes for drift estimation.",
            ),
            _parameter(
                "nblocks",
                "漂移校正时沿探针深度分块的数量。",
                "Number of depth blocks used for drift correction.",
                "1（刚性漂移）",
                "单 shank Neuropixels 可从 1 开始，非刚性漂移可试 5；≤64 通道或稀疏间距约 ≥50 µm 时考虑 0。",
                "Start at 1 for a single-shank Neuropixels probe, try 5 for non-rigid drift, and consider 0 for ≤64 sparse channels around ≥50 µm spacing.",
                "0 跳过漂移校正；分块过多会在 spike 稀少时产生不稳定估计。",
                "Zero disables correction; too many blocks make sparse estimates unstable.",
            ),
            _parameter(
                "Th_universal / Th_learned",
                "通用模板和学习模板的 spike 检测阈值。",
                "Detection thresholds for universal and learned templates.",
                "Kilosort4 当前默认",
                "先用默认；漏检或 unit 时隐时现时每次只降低 1–2，并比较噪声和召回。",
                "Start with defaults; lower by only 1–2 at a time when spikes are missed or units disappear.",
                "阈值降低会检出更多事件，也会增加噪声和计算量。",
                "Lower thresholds detect more events but increase noise and computation.",
            ),
            _parameter(
                "tmin / tmax",
                "参与 sorting 的起止秒数。",
                "Start and end times included in sorting.",
                "整段记录",
                "只有开头或结尾存在已确认伪迹时裁剪，并在审计记录写明。",
                "Crop only confirmed start/end artifacts and document the exclusion.",
                "缩短可加快测试，但短片段结果不能代替整段稳定性评估。",
                "Short ranges speed testing but cannot establish full-session stability.",
            ),
            _parameter(
                "duplicate_spike_ms",
                "同一 unit 中过近 spike 被判为重复并移除的窗口。",
                "Window for removing near-duplicate spikes within a unit.",
                "Kilosort4 默认",
                "仅在 ACG 零点附近出现重复峰且波形证据支持时调整；不得超过 0.5 ms。",
                "Adjust only for a supported duplicate peak around zero in the ACG; never exceed 0.5 ms.",
                "过大会破坏不应期和 ACG/CCG 估计。",
                "Large values corrupt refractory-period and ACG/CCG estimates.",
            ),
        ],
        "recommended": [
            "先用默认参数跑一段代表性数据检查输入和资源，再运行整段记录。",
            "Kilosort 的 drift、depth-time、amplitude、template 和 similarity 图都应查看。",
            "保留 sorter 原生目录；统一格式只服务跨工具衔接，不替代原生证据。",
        ],
        "recommended_en": [
            "Run a representative segment with defaults to validate input and resources before the full session.",
            "Inspect Kilosort drift, depth-time, amplitude, template, and similarity views.",
            "Preserve native sorter directories; normalized output enables interoperability but does not replace native evidence.",
        ],
        "pitfalls": [
            "未实际运行所选 sorter，却显示另一个 sorter 的旧结果。",
            "把真实数据上两个 sorter 的一致度写成准确率。",
            "只看 unit 数量，忽略漂移、重复、振幅和日志。",
        ],
        "pitfalls_en": [
            "Showing an old result from a different sorter when the selected sorter was not run.",
            "Calling cross-sorter agreement on real data accuracy.",
            "Comparing only unit counts while ignoring drift, duplicates, amplitudes, and logs.",
        ],
        "next": "选择一个 active sorting 结果，进入 Unit 质控；必要时再回到本页比较 sorter。",
        "next_en": "Select an active sorting result and continue to Unit QC; return here when sorter comparison is needed.",
    },
    "unit_qc": {
        "narrative": (
            "Sorter 输出的是候选 cluster。Unit 质控把放电率、不应期、信噪比、波形、"
            "振幅随时间和自相关图放在一起，让研究者给出可追溯的保留、MUA、噪声或"
            "待定判断。任何单一阈值都不能替代人工复核。"
        ),
        "narrative_en": (
            "Sorter output contains candidate clusters. Unit QC combines firing rate, "
            "refractory-period evidence, SNR, waveforms, amplitude over time, and ACGs "
            "so the researcher can assign traceable keep, MUA, noise, or uncertain labels. "
            "No single threshold replaces review."
        ),
        "before": "先在 sorting 页确认 active 结果、运行日志和漂移诊断。",
        "before_en": "Confirm the active sorting result, run log, and drift diagnostics first.",
        "operations": [
            _operation(
                "指标散点与筛选",
                "Metric scatter and filters",
                "选择 x/y 指标、阈值和标签，点击点查看 unit。",
                "Choose x/y metrics, thresholds, and labels; click a point to inspect a unit.",
                "发现指标之间的权衡并快速定位异常 unit。",
                "Reveals metric tradeoffs and locates suspicious units.",
                "得到候选筛选集合，不自动改变最终标签。",
                "Produces a candidate subset without changing final labels automatically.",
            ),
            _operation(
                "波形与模板",
                "Waveforms and templates",
                "查看主通道及相邻通道平均波形和变异。",
                "Inspect mean waveforms and variation on the main and neighboring channels.",
                "判断波形是否稳定、空间上是否合理、是否可能为噪声。",
                "Assesses temporal stability, spatial plausibility, and noise.",
                "生成 unit 级波形证据。",
                "Produces unit-level waveform evidence.",
            ),
            _operation(
                "ACG 与 ISI",
                "ACG and ISI",
                "放大 0 ms 附近并检查不应期违例和重复峰。",
                "Zoom around 0 ms and inspect refractory violations and duplicate peaks.",
                "评估污染、重复 spike 和多单元混合。",
                "Evaluates contamination, duplicate spikes, and multi-unit mixtures.",
                "得到时间结构证据和不应期指标。",
                "Produces temporal-structure evidence and refractory metrics.",
            ),
            _operation(
                "人工决定",
                "Manual decision",
                "为 unit 标记 good、MUA、noise 或 uncertain，并写备注。",
                "Label units good, MUA, noise, or uncertain and add a note.",
                "保留研究者判断和阈值版本，支持审计与重做。",
                "Preserves reviewer decisions and threshold versions for audit and revision.",
                "输出可追踪的筛选表和下游 unit 集合。",
                "Outputs a traceable review table and downstream unit set.",
            ),
        ],
        "parameters": [
            _parameter(
                "Firing rate / 放电率",
                "unit 在有效记录时间内每秒的 spike 数。",
                "Spikes per second over valid recording time.",
                "仅报告，不默认剔除",
                "结合脑区、细胞类型、记录时长和稳定性判断。",
                "Interpret with brain region, cell type, duration, and stability.",
                "最低阈值升高会移除稀疏放电 unit，也可能丢失真实低频细胞。",
                "A higher minimum removes sparse units but can discard real low-rate cells.",
            ),
            _parameter(
                "ISI violation window",
                "用于统计不应期违例的时间窗口。",
                "Window used to count refractory-period violations.",
                "2 ms",
                "常从 1–2 ms 开始，并报告具体定义。",
                "Start around 1–2 ms and report the exact definition.",
                "窗口越大违例越多；不同研究的数值不可脱离定义直接比较。",
                "Larger windows count more violations; values are incomparable without the definition.",
            ),
            _parameter(
                "SNR",
                "波形信号幅度相对背景噪声的指标。",
                "Waveform signal magnitude relative to background noise.",
                "仅报告",
                "使用项目内一致算法并结合波形图；不要把跨软件阈值直接照搬。",
                "Use one method consistently and inspect waveforms; do not transfer thresholds blindly across tools.",
                "阈值升高提高保守性，但会对小振幅真实 unit 不利。",
                "Higher thresholds are conservative but penalize real low-amplitude units.",
            ),
            _parameter(
                "Amplitude stability",
                "振幅随时间的变化程度。",
                "Change in spike amplitude over time.",
                "全记录时间线",
                "检查是否单调衰减、突变或只在短时段存在，并与漂移图对应。",
                "Look for decay, jumps, or brief presence and compare with drift diagnostics.",
                "稳定性要求过严会排除真实状态变化；过松会保留漂移/丢失 unit。",
                "Overly strict criteria reject real state changes; loose criteria retain drifting or disappearing units.",
            ),
            _parameter(
                "Contamination threshold",
                "允许的候选污染比例。",
                "Allowed estimated contamination.",
                "不自动设为真值",
                "以 10% 作为可见参考线时必须说明估计方法，并与 ACG/波形共同判断。",
                "If 10% is shown as a guide, report the estimator and review it with ACG and waveforms.",
                "降低阈值会减少 unit 数并提高保守性，但估计本身也有误差。",
                "Lower thresholds reduce unit count and increase conservatism, but the estimate is itself uncertain.",
            ),
        ],
        "recommended": [
            "先看总体分布，再逐个复核临界和高影响 unit。",
            "阈值只生成候选标签；最终决定必须记录 reviewer、时间和备注。",
            "更换 active sorter 后重新计算 QC，不能沿用旧结果。",
        ],
        "recommended_en": [
            "Inspect population distributions first, then review boundary and high-impact units.",
            "Thresholds create candidate labels; final decisions should record reviewer, time, and notes.",
            "Recompute QC after changing the active sorter; never reuse metrics from another result.",
        ],
        "pitfalls": [
            "用单一 SNR 或 ISI 阈值宣布“好神经元”。",
            "把 unit 数量当作 recording yield 而不报告筛选过程。",
            "人工修改标签却不保存审计记录。",
        ],
        "pitfalls_en": [
            "Declaring a good neuron from one SNR or ISI threshold.",
            "Reporting unit count as yield without the screening process.",
            "Changing labels manually without preserving an audit record.",
        ],
        "next": "确定下游 unit 集合后，导入行为与 TTL 并建立统一时间轴。",
        "next_en": "After selecting downstream units, import behavior and TTL data and establish a common timeline.",
    },
    "sync": {
        "narrative": (
            "行为电脑、视频和电生理设备通常各有自己的时钟。同步页把成对 TTL 脉冲"
            "用于估计 offset + slope × behavior_time，并用残差判断是否存在漏脉冲、"
            "错配或非线性漂移。没有对应 TTL 时只能假设共用时钟，界面会明确标注。"
        ),
        "narrative_en": (
            "Behavior computers, cameras, and electrophysiology systems often have "
            "independent clocks. The synchronization page fits offset + slope × "
            "behavior_time from paired TTL pulses and uses residuals to detect missing "
            "pulses, mismatches, or nonlinear drift. Without matching TTLs, NeuroFlow "
            "can only assume a shared clock and labels that assumption explicitly."
        ),
        "before": "准备行为事件 CSV 和可选 TTL CSV；明确每一列的时钟、单位和事件含义。",
        "before_en": "Prepare behavior-event and optional TTL CSV files and identify each column's clock, unit, and event meaning.",
        "operations": [
            _operation(
                "导入行为事件",
                "Import behavior events",
                "选择包含 time_seconds、trial、condition 和 event_type 的 CSV。",
                "Select a CSV with time_seconds, trial, condition, and event_type.",
                "建立 trial 语义和行为时钟中的事件序列。",
                "Builds trial semantics and the event sequence in the behavior clock.",
                "项目保存事件表和源文件路径。",
                "Stores the event table and source path in the project.",
            ),
            _operation(
                "导入 TTL",
                "Import TTL pulses",
                "选择包含与行为同步脉冲一一对应的电生理时间 CSV。",
                "Select a CSV containing ephys-clock pulses corresponding to behavior sync pulses.",
                "建立两个设备时钟之间的可估计映射。",
                "Creates an estimable mapping between device clocks.",
                "显示可匹配数量、缺失和重复脉冲。",
                "Shows matched counts, missing pulses, and duplicates.",
            ),
            _operation(
                "拟合统一时间轴",
                "Fit common timeline",
                "按事件顺序匹配并拟合截距与斜率。",
                "Pair pulses in order and fit intercept and slope.",
                "校正起始偏移和线性时钟漂移。",
                "Corrects initial offset and linear clock drift.",
                "生成 ephys 秒时间、残差、drift ppm 和 trial 表。",
                "Produces ephys-clock seconds, residuals, drift ppm, and a trial table.",
            ),
            _operation(
                "检查同步证据",
                "Inspect synchronization evidence",
                "查看残差随时间、事件计数和异常配对。",
                "Inspect residuals over time, event counts, and suspect pairs.",
                "判断线性映射是否足够，是否需要重新配对或分段。",
                "Determines whether a linear map is adequate or pairing/segmentation must change.",
                "保留同步质量报告供所有事件对齐分析引用。",
                "Preserves a synchronization report for every event-aligned analysis.",
            ),
        ],
        "parameters": [
            _parameter(
                "Behavior time column",
                "行为设备时间戳所在列。",
                "Column containing behavior-device timestamps.",
                "time_seconds",
                "优先转换为秒并保留原始列；若为帧号需提供帧率或逐帧时间。",
                "Convert to seconds while retaining the source column; frame indices require frame rate or per-frame timestamps.",
                "单位错误会产生 1000 倍或采样率倍的偏移。",
                "A unit mistake creates 1000× or sampling-rate-scale errors.",
            ),
            _parameter(
                "TTL pairing",
                "行为脉冲与电生理脉冲如何对应。",
                "How behavior and ephys pulses are paired.",
                "按顺序一一配对",
                "先核对数量和间隔；有漏脉冲时用间隔序列定位后再配对。",
                "Check counts and intervals first; locate missing pulses from interval patterns before pairing.",
                "一个漏脉冲会让后续全部按序配对错位。",
                "One missing pulse shifts all subsequent order-based pairs.",
            ),
            _parameter(
                "Clock model",
                "从行为时钟映射到电生理时钟的函数。",
                "Function mapping behavior time to ephys time.",
                "offset + slope × time",
                "先用线性模型；残差呈弯曲或分段跳变时才考虑分段/非线性。",
                "Start linear; use segmented or nonlinear models only for curved residuals or clock jumps.",
                "模型过于复杂会拟合脉冲噪声；过于简单会留下系统漂移。",
                "An overly complex model fits pulse jitter; an overly simple model leaves systematic drift.",
            ),
            _parameter(
                "Residual tolerance",
                "匹配后允许的最大时间误差。",
                "Maximum allowed timing error after alignment.",
                "报告实际值，不自动隐藏",
                "根据任务时间尺度和设备精度设定；毫秒级 spike 响应需更严格。",
                "Set from task timescale and device precision; millisecond spike responses require tighter limits.",
                "容差放宽会保留错配；过严会剔除正常 TTL 抖动。",
                "Loose tolerance retains mismatches; strict tolerance rejects normal TTL jitter.",
            ),
            _parameter(
                "Shared-clock assumption",
                "无 TTL 时是否把行为秒时间直接当作电生理秒时间。",
                "Whether behavior seconds are treated directly as ephys seconds without TTLs.",
                "仅在未提供 TTL 时启用并警告",
                "只有系统确实共享硬件时钟或已在外部完成同步时使用。",
                "Use only with a shared hardware clock or externally completed synchronization.",
                "无法检测起始偏移和漂移，结论风险必须写入报告。",
                "Cannot detect offset or drift; the limitation must appear in the report.",
            ),
        ],
        "recommended": [
            "导入后先看事件和 TTL 数量、间隔，再拟合。",
            "残差图必须覆盖整段记录，不能只报告平均误差。",
            "同步映射、源列、单位和排除配对全部保存到项目。",
        ],
        "recommended_en": [
            "Inspect event/TTL counts and intervals before fitting.",
            "Residual plots must cover the full session, not only a mean error.",
            "Save the mapping, source columns, units, and excluded pairs in the project.",
        ],
        "pitfalls": [
            "把行为毫秒当成秒。",
            "有漏脉冲仍按行号强制一一对应。",
            "没有 TTL 却报告精确同步误差。",
        ],
        "pitfalls_en": [
            "Treating behavior milliseconds as seconds.",
            "Forcing row-by-row pairing after a missing pulse.",
            "Reporting precise synchronization error without TTL evidence.",
        ],
        "next": "用同步后的 trial 表先检查行为质量，再进行事件对齐神经分析。",
        "next_en": "Use the synchronized trial table to inspect behavior before event-aligned neural analysis.",
    },
    "behavior": {
        "narrative": (
            "行为分析先回答实验是否按设计执行：各条件有多少 trial、选择是否平衡、"
            "反应时是否合理、缺失和排除发生在哪里。只有行为结构可靠，神经响应和"
            "机器学习标签才有可解释含义。"
        ),
        "narrative_en": (
            "Behavior analysis first asks whether the experiment ran as designed: "
            "trial counts per condition, choice balance, reaction times, missing values, "
            "and exclusions. Neural responses and machine-learning labels become "
            "interpretable only after behavior structure is reliable."
        ),
        "before": "同步页已生成统一秒时间和 trial 表，并明确 trial 开始、事件和结束。",
        "before_en": "The synchronization page has produced a common timeline and trial table with start, event, and end definitions.",
        "operations": [
            _operation(
                "条件计数",
                "Condition counts",
                "查看每个刺激、选择、结果或组别的 trial 数。",
                "Inspect trial counts by stimulus, choice, outcome, or group.",
                "发现类别不平衡和设计遗漏。",
                "Finds class imbalance and missing design cells.",
                "输出可用于统计和解码的有效样本数。",
                "Outputs valid sample counts for statistics and decoding.",
            ),
            _operation(
                "反应时",
                "Reaction time",
                "绘制分布、条件比较和异常 trial。",
                "Plot distributions, condition comparisons, and outlier trials.",
                "识别过快猜测、超时和记录错误。",
                "Identifies anticipatory responses, timeouts, and logging errors.",
                "生成反应时变量和排除候选。",
                "Produces reaction-time variables and exclusion candidates.",
            ),
            _operation(
                "心理测量曲线",
                "Psychometric curve",
                "按刺激强度计算选择比例和样本量。",
                "Compute choice probability and sample size by stimulus level.",
                "检查行为是否随任务变量系统变化。",
                "Checks whether behavior varies systematically with task variables.",
                "输出曲线、每点 trial 数和拟合参数。",
                "Outputs the curve, trial count per point, and fit parameters.",
            ),
            _operation(
                "trial 排除",
                "Trial exclusions",
                "依据预先定义规则标记缺失、超时、伪迹或异常值。",
                "Flag missing, timeout, artifact, or outlier trials using predefined rules.",
                "让排除发生在看神经结果之前，减少结果导向筛选。",
                "Applies exclusions before neural results are viewed to reduce outcome-driven filtering.",
                "保留原 trial 和 exclusion_reason，不物理删除。",
                "Retains every trial and an exclusion_reason rather than deleting rows.",
            ),
        ],
        "parameters": [
            _parameter(
                "Condition column",
                "用于分组比较的 trial 字段。",
                "Trial field used for group comparisons.",
                "condition",
                "使用实验程序原始标签并建立数据字典。",
                "Use original task labels and maintain a data dictionary.",
                "重新编码会改变分组和样本量，必须保留映射。",
                "Recoding changes groups and counts; preserve the mapping.",
            ),
            _parameter(
                "Reaction-time start/end",
                "计算反应时所用的两个事件。",
                "Two events defining reaction time.",
                "stimulus_onset → response",
                "按科学问题明确；运动开始、按键和奖励不能混用。",
                "Define from the scientific question; movement onset, button press, and reward are not interchangeable.",
                "终点事件不同会改变数值和神经对齐解释。",
                "Different endpoints change both values and neural interpretation.",
            ),
            _parameter(
                "Minimum trials",
                "一个条件进入统计或解码所需的最低有效 trial 数。",
                "Minimum valid trials required for a condition.",
                "仅警告，不自动剔除",
                "依据效应大小、变异和验证方案做功效评估；不要固定套用一个数。",
                "Use power analysis based on effect, variance, and validation design rather than one universal count.",
                "阈值越高条件越稳定但可用 session 越少。",
                "Higher thresholds improve stability but exclude more sessions.",
            ),
            _parameter(
                "Outlier rule",
                "反应时或连续行为变量的异常值定义。",
                "Rule defining outliers in reaction time or continuous behavior.",
                "不默认删除",
                "优先使用任务定义边界或稳健规则，并报告剔除数量。",
                "Prefer task-defined limits or robust rules and report excluded counts.",
                "事后调整边界可能改变条件效应并引入偏差。",
                "Post-hoc limits can change condition effects and introduce bias.",
            ),
        ],
        "recommended": [
            "行为图先于神经图生成并保存。",
            "每个图点都可点击查看刺激水平、样本量和原始 trial。",
            "排除规则保存为字段和日志，不覆盖原始 trial 表。",
        ],
        "recommended_en": [
            "Generate and save behavior figures before neural figures.",
            "Make every plotted point inspectable for stimulus level, count, and source trials.",
            "Store exclusion rules as fields and logs without overwriting the original trial table.",
        ],
        "pitfalls": [
            "类别严重不平衡仍只报告普通准确率。",
            "看完神经差异后再调整行为排除规则。",
            "把 trial、session 和动物混为一个样本层级。",
        ],
        "pitfalls_en": [
            "Reporting ordinary accuracy despite severe class imbalance.",
            "Changing behavioral exclusions after seeing neural differences.",
            "Confusing trial, session, and animal sampling levels.",
        ],
        "next": "锁定有效 trial 和条件标签后，进入事件响应、spike train、LFP 或联合分析。",
        "next_en": "After locking valid trials and condition labels, continue to event response, spike-train, LFP, or joint analyses.",
    },
    "analysis": {
        "narrative": (
            "神经活动页不是一张固定 PSTH，而是四类可独立运行的分析入口：事件对齐"
            "响应、spike train 统计、LFP 频谱/时频，以及 spike-field 耦合。每个子分析"
            "都有自己的输入、参数、图和表；未运行时显示输入预览和运行目的，不伪造结果。"
        ),
        "narrative_en": (
            "The neural page is not a single fixed PSTH. It contains independently "
            "runnable event-response, spike-train, LFP spectral/time-frequency, and "
            "spike-field coupling analyses. Every sub-analysis has its own inputs, "
            "settings, figures, and tables; before execution it shows an input preview, "
            "never fabricated results."
        ),
        "before": "确认 active units、同步事件、有效 trial；LFP 或耦合分析还需要原始/LFP 电压。",
        "before_en": "Confirm active units, synchronized events, and valid trials; LFP and coupling also require voltage data.",
        "operations": [
            _operation(
                "事件对齐 Raster/PSTH",
                "Event-aligned Raster/PSTH",
                "选择事件、窗口、bin、平滑、baseline 和条件。",
                "Choose event, window, bin, smoothing, baseline, and condition.",
                "描述 unit 或群体在事件前后的时间响应。",
                "Describes unit or population responses around an event.",
                "输出 raster、PSTH、热图、响应窗口和 trial 级特征。",
                "Outputs raster, PSTH, heatmap, response windows, and trial-level features.",
            ),
            _operation(
                "Spike train 统计",
                "Spike-train statistics",
                "选择 CV2、Lv、Fano、ACG/CCH、STTC 或距离。",
                "Choose CV2, Lv, Fano, ACG/CCH, STTC, or spike-train distances.",
                "量化放电规律性、变异和神经元间时间关系。",
                "Quantifies regularity, variability, and temporal relationships between units.",
                "生成单位明确的指标表和 correlogram。",
                "Produces metrics with explicit units and correlograms.",
            ),
            _operation(
                "LFP 分析",
                "LFP analysis",
                "运行 PSD、频带功率、coherence 或时频图。",
                "Run PSD, band power, coherence, or time-frequency analysis.",
                "描述振荡功率、跨通道关系和事件相关频谱变化。",
                "Describes oscillatory power, cross-channel relations, and event-related spectral changes.",
                "输出频谱、时频矩阵、频带汇总和方法参数。",
                "Outputs spectra, time-frequency matrices, band summaries, and method settings.",
            ),
            _operation(
                "Spike-field 耦合",
                "Spike-field coupling",
                "选择相位频带、参考通道、spike 集合和 surrogate。",
                "Choose phase band, reference channel, spike set, and surrogates.",
                "检验 spike 是否偏好某一 LFP 相位，并评估机会水平。",
                "Tests whether spikes prefer an LFP phase and evaluates chance level.",
                "输出相位分布、向量强度、Rayleigh/置换证据和 PAC/STA。",
                "Outputs phase distributions, vector strength, Rayleigh/permutation evidence, and PAC/STA.",
            ),
        ],
        "parameters": [
            _parameter(
                "Alignment event",
                "所有 trial 的时间零点。",
                "Time zero for every trial.",
                "stimulus_onset（取决于事件表）",
                "按假设选择；刺激、运动、选择和奖励回答不同问题。",
                "Choose from the hypothesis; stimulus, movement, choice, and reward answer different questions.",
                "更换事件会改变响应时间解释，不能只挑最显著者。",
                "Changing the event changes temporal interpretation and must not be significance-driven.",
            ),
            _parameter(
                "Window",
                "事件前后截取的时间范围。",
                "Time range extracted around the event.",
                "-1 到 +2 s",
                "覆盖 baseline 和预期响应，同时避免相邻 trial/事件重叠。",
                "Cover baseline and expected response while avoiding neighboring trials or events.",
                "过短漏掉慢响应；过长增加重叠和多重比较。",
                "Short windows miss slow responses; long windows increase overlap and multiplicity.",
            ),
            _parameter(
                "Bin size",
                "PSTH 或计数特征的时间分箱宽度。",
                "Temporal bin width for PSTH or count features.",
                "50 ms",
                "快速感觉响应可用 5–20 ms；行为/群体趋势常用 20–100 ms，并做敏感性比较。",
                "Use 5–20 ms for fast sensory responses and 20–100 ms for behavioral/population trends, with sensitivity checks.",
                "小 bin 提高时间分辨率但噪声大；大 bin 平滑响应并降低峰值。",
                "Small bins improve resolution but are noisy; large bins smooth responses and lower peaks.",
            ),
            _parameter(
                "Smoothing",
                "对分箱放电率施加的平滑核与宽度。",
                "Kernel and width applied to binned firing rates.",
                "默认最小或关闭",
                "图示可平滑，统计优先使用未平滑 trial 特征；报告核和宽度。",
                "Smoothing is acceptable for display; statistics should prefer unsmoothed trial features and report the kernel.",
                "平滑越强峰越低、响应越宽，可能制造相邻时间相关。",
                "Stronger smoothing lowers peaks, broadens responses, and induces temporal dependence.",
            ),
            _parameter(
                "PSD method",
                "功率谱估计方法和分段设置。",
                "Power-spectral estimator and segmentation settings.",
                "Welch",
                "平稳片段从 Welch 开始；报告窗长、重叠、频率分辨率和单位。",
                "Start with Welch for stationary segments and report window, overlap, resolution, and units.",
                "长窗提高频率分辨率但降低时间局部性；短窗相反。",
                "Long windows improve frequency resolution but reduce temporal localization, and vice versa.",
            ),
            _parameter(
                "Surrogates",
                "通过时间移位或标签打乱建立机会分布的次数。",
                "Number of time shifts or label shuffles used for a chance distribution.",
                "200（演示）",
                "正式分析通常至少 1,000，尾部 p 值需要更多；固定随机种子。",
                "Use at least 1,000 for formal analysis and more for tail p-values; fix the random seed.",
                "次数少运行快但 p 值分辨率低；次数多更稳定但耗时增加。",
                "Fewer runs are faster but give coarse p-values; more runs are stable but expensive.",
            ),
        ],
        "recommended": [
            "每次只运行一个明确子分析，并在运行前阅读输入和参数摘要。",
            "图和统计共享同一 trial、窗口和条件定义，但统计不依赖图形平滑。",
            "保留每个子图对应的数据表，允许单独编辑和导出。",
        ],
        "recommended_en": [
            "Run one clearly defined sub-analysis at a time and review its input/settings summary first.",
            "Figures and statistics share trial, window, and condition definitions, while inference avoids display smoothing.",
            "Retain the data table behind every panel for independent editing and export.",
        ],
        "pitfalls": [
            "未运行新选项时仍显示其他分析的旧图。",
            "用平滑后的 PSTH 每个时间点直接做大量 t 检验。",
            "LFP 未抗混叠降采样或 spike-field 使用同一电极造成 spike 泄漏。",
        ],
        "pitfalls_en": [
            "Showing an old figure from another analysis before the new selection runs.",
            "Applying many pointwise t-tests directly to a smoothed PSTH.",
            "Downsampling LFP without anti-aliasing or allowing spike leakage in same-electrode coupling.",
        ],
        "next": "将 trial 级神经指标送入统计页，或构建 trial × feature 矩阵进入机器学习。",
        "next_en": "Send trial-level neural metrics to Statistics or build a trial-by-feature matrix for Machine Learning.",
    },
    "statistics": {
        "narrative": (
            "统计页从“样本是什么”开始，而不是从检验名称开始。trial 嵌套于 session，"
            "unit 嵌套于动物；配对、重复测量和层级结构决定了哪些比较合法。页面同时"
            "报告效应量、置信区间和多重比较处理，不把 p 值作为唯一结论。"
        ),
        "narrative_en": (
            "Statistics begins with the sampling unit, not a test name. Trials are "
            "nested in sessions and units in animals; pairing, repeated measures, and "
            "hierarchy determine valid comparisons. The page reports effects, confidence "
            "intervals, and multiplicity handling rather than treating p-values as the only result."
        ),
        "before": "准备未平滑的 trial 级指标、条件、unit/session/animal 标识和排除规则。",
        "before_en": "Prepare unsmoothed trial-level metrics, conditions, unit/session/animal IDs, and exclusions.",
        "operations": [
            _operation(
                "设计检查",
                "Design check",
                "指定样本单位、配对关系、层级和主要比较。",
                "Specify sampling unit, pairing, hierarchy, and primary comparison.",
                "防止伪重复和把嵌套样本当独立样本。",
                "Prevents pseudoreplication and treating nested samples as independent.",
                "生成可审计的统计设计摘要。",
                "Produces an auditable statistical-design summary.",
            ),
            _operation(
                "参数/非参数比较",
                "Parametric/nonparametric comparison",
                "根据设计选择 t/Welch/ANOVA 或 Wilcoxon/Mann–Whitney/Kruskal。",
                "Choose t/Welch/ANOVA or Wilcoxon/Mann–Whitney/Kruskal from the design.",
                "在假设和数据结构匹配的前提下比较条件。",
                "Compares conditions under explicit assumptions and data structure.",
                "输出统计量、p 值、效应量、置信区间和样本数。",
                "Outputs statistic, p-value, effect, confidence interval, and sample size.",
            ),
            _operation(
                "置换/Bootstrap",
                "Permutation/bootstrap",
                "按合法交换单位打乱标签或重采样。",
                "Shuffle labels or resample at the legal exchangeability unit.",
                "在分布假设较弱时建立零分布或置信区间。",
                "Builds null distributions or intervals with fewer distributional assumptions.",
                "保存随机种子、次数和完整机会分布。",
                "Saves random seed, repetitions, and the complete chance distribution.",
            ),
            _operation(
                "混合效应模型",
                "Mixed-effects model",
                "设置固定效应和 animal/session/unit 随机效应。",
                "Set fixed effects and animal/session/unit random effects.",
                "处理分层、缺失和不平衡重复测量。",
                "Handles hierarchical, missing, and unbalanced repeated measures.",
                "输出模型式、系数、区间、收敛和诊断。",
                "Outputs formula, coefficients, intervals, convergence, and diagnostics.",
            ),
        ],
        "parameters": [
            _parameter(
                "Sampling unit",
                "进入推断统计的独立观察单位。",
                "Independent observational unit used for inference.",
                "必须由用户确认",
                "动物层结论通常以动物为独立单位；unit/session 可作为嵌套层。",
                "Animal-level claims usually require animals as independent units, with units/sessions nested.",
                "选得过细会虚增 n 和显著性；过粗会损失信息。",
                "Too fine inflates n and significance; too coarse loses information.",
            ),
            _parameter(
                "Paired",
                "两个条件是否来自同一对象或匹配单元。",
                "Whether conditions come from the same or matched observational unit.",
                "根据设计",
                "同一 unit/session/animal 的前后比较使用配对；不同对象使用非配对。",
                "Use paired tests for repeated observations from the same unit/session/animal.",
                "配对指定错误会改变误差项和检验效能。",
                "Incorrect pairing changes the error term and statistical power.",
            ),
            _parameter(
                "Alpha",
                "预先定义的 I 类错误阈值。",
                "Predefined type-I error threshold.",
                "0.05",
                "在分析前设定，并与多重比较方法一起报告。",
                "Set before analysis and report together with multiplicity correction.",
                "降低 alpha 更保守但增加漏检；不能为获得显著而事后调整。",
                "Lower alpha is conservative but increases misses; never change it post hoc for significance.",
            ),
            _parameter(
                "Multiple comparison",
                "一组相关检验的错误率控制方法。",
                "Method controlling error across a family of tests.",
                "FDR Benjamini–Hochberg",
                "探索性多单元/多时间窗可用 FDR；少量预设比较可用 Holm；报告 family 定义。",
                "Use FDR for exploratory multi-unit/time tests and Holm for a few planned comparisons; define the family.",
                "更严格校正减少假阳性但降低功效；不定义检验族会使校正失去意义。",
                "Stricter correction reduces false positives and power; correction is meaningless without a defined family.",
            ),
            _parameter(
                "Resamples",
                "置换或 bootstrap 重复次数。",
                "Number of permutation or bootstrap repetitions.",
                "1,000",
                "快速预览 200–1,000；最终估计常用 5,000–10,000 并固定种子。",
                "Use 200–1,000 for preview and often 5,000–10,000 for final estimates with a fixed seed.",
                "次数决定 p 值/区间的蒙特卡洛稳定性和运行时间。",
                "Controls Monte Carlo stability of p-values/intervals and runtime.",
            ),
        ],
        "recommended": [
            "先生成统计设计卡，再允许选择检验。",
            "同时报告原始数据点、效应量、置信区间、p 值和校正方法。",
            "将完整统计表与生成图所用汇总分开保存。",
        ],
        "recommended_en": [
            "Create a statistical-design card before enabling test selection.",
            "Report raw observations, effect, confidence interval, p-value, and correction together.",
            "Save the full statistical table separately from figure summaries.",
        ],
        "pitfalls": [
            "3 只动物的 300 个 unit 被当作 n=300 独立样本。",
            "对每个 PSTH 时间 bin 做检验却不校正。",
            "只报告 p 值，不报告方向、大小和不确定性。",
        ],
        "pitfalls_en": [
            "Treating 300 units from three animals as n=300 independent observations.",
            "Testing every PSTH bin without multiplicity control.",
            "Reporting only p-values without direction, magnitude, or uncertainty.",
        ],
        "next": "统计结果可直接进入论文导出；若问题是预测标签或连续变量，进入机器学习。",
        "next_en": "Statistical results can go to publication export; prediction questions continue to Machine Learning.",
    },
    "decoding": {
        "narrative": (
            "机器学习页把神经活动转换为 trial × feature 矩阵，并把预处理、特征选择和"
            "模型全部放入交叉验证内部。核心不是寻找最高分，而是建立没有数据泄漏、"
            "与 shuffle 基线比较、能跨 session/动物泛化的评估。"
        ),
        "narrative_en": (
            "Machine Learning converts neural activity to a trial-by-feature matrix "
            "and places preprocessing, feature selection, and the model inside cross-validation. "
            "The goal is not the highest score but a leakage-free evaluation against a "
            "shuffle baseline with session/animal generalization."
        ),
        "before": "确定预测目标、特征时间窗、分组变量、类别平衡和最小样本量。",
        "before_en": "Define prediction target, feature window, grouping variable, class balance, and minimum sample size.",
        "operations": [
            _operation(
                "分类",
                "Classification",
                "选择 Logistic regression、SVM、Random forest、XGBoost 等模型。",
                "Choose Logistic regression, SVM, Random forest, XGBoost, or another model.",
                "预测离散刺激、选择或结果标签。",
                "Predicts discrete stimulus, choice, or outcome labels.",
                "输出 balanced accuracy、F1、AUC、混淆矩阵和每折分数。",
                "Outputs balanced accuracy, F1, AUC, confusion matrix, and fold scores.",
            ),
            _operation(
                "回归",
                "Regression",
                "选择线性、Ridge、随机森林等回归模型。",
                "Choose linear, Ridge, random-forest, or another regressor.",
                "预测位置、速度、反应时或连续刺激变量。",
                "Predicts position, speed, reaction time, or continuous stimulus values.",
                "输出 R²、MAE、预测-真实图和残差。",
                "Outputs R², MAE, predicted-versus-observed plots, and residuals.",
            ),
            _operation(
                "时间分辨解码",
                "Time-resolved decoding",
                "在滑动时间 bin 内重复完整交叉验证。",
                "Repeat the complete cross-validation inside sliding time bins.",
                "估计可预测信息随事件时间的变化。",
                "Estimates how predictive information changes around an event.",
                "输出时间曲线、机会分布和多重比较结果。",
                "Outputs a time course, chance distribution, and multiplicity results.",
            ),
            _operation(
                "PCA 与聚类",
                "PCA and clustering",
                "对神经群体特征降维或无监督分组。",
                "Reduce population features or perform unsupervised grouping.",
                "探索群体结构，不把可视化分离自动当作统计证据。",
                "Explores population structure without treating visual separation as inference.",
                "输出解释方差、载荷、投影和聚类稳定性。",
                "Outputs explained variance, loadings, projections, and clustering stability.",
            ),
        ],
        "parameters": [
            _parameter(
                "Feature window",
                "每个 trial 提取神经特征的时间范围。",
                "Time range used to extract neural features for each trial.",
                "0–0.5 s（依任务而定）",
                "根据因果时间关系预先定义；预测行为时避免使用行为发生后的信息。",
                "Predefine from causal timing; do not use post-behavior information to predict behavior.",
                "更长窗口包含更多信息，也更容易混入后续事件和运动。",
                "Long windows contain more information but can include later events and movement.",
            ),
            _parameter(
                "Cross-validation",
                "训练/验证数据划分与重复方式。",
                "Train/validation split and repetition scheme.",
                "5-fold stratified 或 grouped",
                "同一 session/动物不能跨折泄漏时使用 GroupKFold/LeaveOneGroupOut。",
                "Use GroupKFold or LeaveOneGroupOut when sessions or animals must not cross folds.",
                "随机 trial 划分通常分数更高，但可能只学到 session 身份。",
                "Random trial splits often score higher but may learn session identity.",
            ),
            _parameter(
                "Scaling",
                "特征标准化或归一化。",
                "Feature standardization or normalization.",
                "线性/SVM 模型使用 StandardScaler",
                "必须在每个训练折拟合，再应用到验证折。",
                "Fit within every training fold and apply to its validation fold.",
                "全数据先标准化会泄漏验证集均值和方差。",
                "Scaling the full dataset first leaks validation means and variances.",
            ),
            _parameter(
                "Class weighting",
                "对不平衡类别的损失权重。",
                "Loss weights for imbalanced classes.",
                "balanced（不平衡时）",
                "先报告类别数；使用权重或重采样时只能在训练折内完成。",
                "Report class counts first; weighting or resampling must occur inside training folds.",
                "会改变决策边界和概率校准，不能只报告普通准确率。",
                "Changes decision boundaries and calibration; ordinary accuracy is insufficient.",
            ),
            _parameter(
                "Permutation count",
                "打乱标签并重跑完整验证的次数。",
                "Number of label shuffles with complete re-validation.",
                "200（演示）",
                "正式结果至少 1,000，并保持分组结构不被破坏。",
                "Use at least 1,000 for final results while preserving group structure.",
                "只打乱一次不能形成稳定机会分布；错误打乱会破坏嵌套结构。",
                "One shuffle is unstable; invalid shuffling destroys nesting.",
            ),
        ],
        "recommended": [
            "先建立线性基线，再比较复杂模型。",
            "模型、特征选择、缩放和超参数搜索全部封装在验证循环内。",
            "报告每折分数、shuffle 分布和跨组泛化，而不是一个最高分。",
        ],
        "recommended_en": [
            "Establish a linear baseline before comparing complex models.",
            "Place the model, feature selection, scaling, and hyperparameter search inside validation.",
            "Report fold scores, shuffle distribution, and cross-group generalization rather than one best score.",
        ],
        "pitfalls": [
            "同一 session 的相邻 trial 同时进入训练和测试。",
            "用全数据选择神经元后再交叉验证。",
            "比较多个模型后只展示最高结果，不披露选择过程。",
        ],
        "pitfalls_en": [
            "Putting adjacent trials from the same session into both train and test.",
            "Selecting units on all data before cross-validation.",
            "Showing only the best model after undisclosed model comparison.",
        ],
        "next": "把模型配置、验证拆分、分数表和图送入论文与复现页。",
        "next_en": "Send model configuration, validation splits, score tables, and figures to Publication and Reproducibility.",
    },
    "export": {
        "narrative": (
            "导出页把图、绘图数据、统计表、Methods、软件环境和工作流绑定在一起。"
            "图形编辑不会改写分析数据；重新计算和视觉调整是两条独立审计记录。"
            "项目保存后，可通过 neuroflow_project.json 恢复已完成步骤和 active 结果。"
        ),
        "narrative_en": (
            "Export binds figures to plotted data, statistical tables, Methods, the "
            "software environment, and the workflow. Visual edits never rewrite analysis "
            "data; recomputation and styling have separate audit trails. A saved "
            "neuroflow_project.json restores completed stages and the active result."
        ),
        "before": "确认图中的坐标、单位、样本量、误差定义和统计标注均来自已保存结果。",
        "before_en": "Verify axes, units, sample sizes, error definitions, and annotations against saved results.",
        "operations": [
            _operation(
                "编辑当前图",
                "Edit current figure",
                "双击坐标轴或打开 Figure Studio，修改对象级样式。",
                "Double-click an axis or open Figure Studio for object-level styling.",
                "在不重算数据的前提下完成论文版式。",
                "Creates publication styling without recomputing data.",
                "修改线、点、柱、热图、文字、坐标、刻度、网格和图例。",
                "Edits lines, markers, bars, images, text, axes, ticks, grids, and legends.",
            ),
            _operation(
                "单独保存子图",
                "Save one panel",
                "从图表面板选择子图，设置精确尺寸并导出。",
                "Select a panel, set exact dimensions, and export it.",
                "避免整页截图造成分辨率和排版问题。",
                "Avoids screenshots with poor resolution and layout.",
                "输出 PNG、SVG 或 PDF，并保留背景和字体设置。",
                "Exports PNG, SVG, or PDF with background and font settings.",
            ),
            _operation(
                "导出数据与统计表",
                "Export data and statistics",
                "保存当前图背后的 x/y/分组数据和完整统计结果。",
                "Save x/y/group data behind the figure and the complete statistical output.",
                "让读者能从图回到数值，并允许在外部软件复核。",
                "Links the figure back to values and enables external verification.",
                "输出 CSV/JSON 表和来源索引。",
                "Exports CSV/JSON tables and a provenance index.",
            ),
            _operation(
                "保存/恢复项目",
                "Save/restore project",
                "点击保存项目，之后从首页打开 neuroflow_project.json。",
                "Save the project, then reopen neuroflow_project.json from the home page.",
                "恢复数据来源、工作流状态、sorter 结果、分析表和审计日志。",
                "Restores sources, workflow state, sorter results, analysis tables, and audit log.",
                "重新打开后定位到上次保存页面，已完成节点可直接查看。",
                "Reopens at the last saved page with completed stages available for inspection.",
            ),
        ],
        "parameters": [
            _parameter(
                "Format",
                "图像文件类型。",
                "Figure file type.",
                "PNG + SVG",
                "PNG 用于快速预览；SVG/PDF 用于矢量编辑和出版。",
                "Use PNG for preview and SVG/PDF for vector editing and publication.",
                "栅格格式受 DPI 限制；矢量格式保留线和文字对象。",
                "Raster output depends on DPI; vector output preserves line and text objects.",
            ),
            _parameter(
                "Figure size",
                "输出宽度和高度。",
                "Output width and height.",
                "按当前图",
                "按期刊单栏/双栏毫米尺寸设置，再检查最长标签是否溢出。",
                "Set journal single/double-column dimensions in millimeters and inspect long labels.",
                "尺寸改变会影响文字相对大小和 panel 间距。",
                "Changing dimensions alters relative text size and panel spacing.",
            ),
            _parameter(
                "DPI",
                "栅格输出每英寸像素数。",
                "Pixels per inch for raster output.",
                "300",
                "线图 300–600 DPI；显微/热图按期刊要求和原始分辨率。",
                "Use 300–600 DPI for line art and follow journal/source resolution for images or heatmaps.",
                "DPI 越高文件越大，但不能增加原始数据分辨率。",
                "Higher DPI increases file size but cannot add source-data resolution.",
            ),
            _parameter(
                "Axis/grid/spine",
                "坐标轴线宽、长度、刻度、网格和边框显示。",
                "Axis line width, extent, ticks, grid, and spine visibility.",
                "NeuroFlow 标准主题",
                "按图类型调整并保持同一 Figure 内一致；不要用装饰网格掩盖数据。",
                "Adjust by plot type and keep a figure consistent; do not let decorative grids obscure data.",
                "粗线提高可见性但会压缩小 panel；网格过强会与数据竞争。",
                "Thick lines improve visibility but crowd small panels; strong grids compete with data.",
            ),
            _parameter(
                "Project source mode",
                "项目使用外部只读索引还是内部原始副本。",
                "Whether the project uses an external read-only link or an internal raw copy.",
                "取决于导入选择",
                "长期归档前检查所有外部路径；需要独立移动时复制原始数据或使用可访问共享路径。",
                "Before archiving, verify external paths; copy raw data or use stable shared storage for portability.",
                "清单始终可打开，但外部源丢失后依赖原始电压的步骤不能重跑。",
                "The manifest remains readable, but raw-dependent stages cannot rerun if an external source is missing.",
            ),
        ],
        "recommended": [
            "每张论文图同时保存矢量图、绘图数据、统计表和生成参数。",
            "保存项目后关闭并重新打开一次，验证恢复位置和关键结果。",
            "对外分享前检查源路径、许可证、匿名化和未发表数据权限。",
        ],
        "recommended_en": [
            "Save vector output, plotted data, statistical tables, and generation settings for every publication figure.",
            "After saving, close and reopen once to verify restore position and key results.",
            "Before sharing, check source paths, licenses, anonymization, and unpublished-data permissions.",
        ],
        "pitfalls": [
            "只保存截图，没有绘图数据和统计来源。",
            "编辑图中文字后与实际单位或样本量不一致。",
            "只读索引指向个人临时目录，却把项目当作可独立归档。",
        ],
        "pitfalls_en": [
            "Saving only screenshots without plotted data or statistical provenance.",
            "Editing labels until units or sample counts no longer match results.",
            "Treating a project linked to a personal temporary folder as a portable archive.",
        ],
        "next": "完成复现包后仍由研究者负责科学解释、论文组织和最终数据共享决定。",
        "next_en": "After the reproducibility bundle, the researcher remains responsible for interpretation, manuscript structure, and data-sharing decisions.",
    },
}


def detail_value(value: Any, language: str = "zh_CN") -> Any:
    if isinstance(value, dict):
        return {
            key: detail_value(item, language)
            for key, item in value.items()
            if not key.endswith("_en")
        }
    if isinstance(value, list):
        return [detail_value(item, language) for item in value]
    return value


def localized(detail: dict[str, Any], field: str, language: str = "zh_CN") -> Any:
    if language == "en_US":
        return detail.get(f"{field}_en", detail[field])
    return detail[field]


def localized_rows(
    detail: dict[str, Any],
    field: str,
    language: str = "zh_CN",
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source in detail.get(field, []):
        row: dict[str, str] = {}
        for key, value in source.items():
            if key.endswith("_en"):
                continue
            row[key] = (
                source.get(f"{key}_en", value)
                if language == "en_US"
                else value
            )
        rows.append(row)
    return rows
