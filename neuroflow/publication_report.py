"""Accountable publication outline; never invent biological conclusions."""
from __future__ import annotations
import hashlib
import html
import json
from pathlib import Path

# Content-based grouping, never significance-based selection.
MAIN = ('behavior', 'raster_psth_population', 'statistics')
CAPTIONS = {
    'behavior': ('Behavioral context', 'Observed event timing and available trial summaries. Event rows are not necessarily independent trials.', '行为发生的时间与已有试次信息。事件条数不等于独立试次数。'),
    'raster_psth_population': ('Event-aligned neural activity', '(a) Raster for the displayed unit, one event per row. (b) Mean PSTH, shading: SEM across available events. (c) Baseline-normalized population activity. (d) Per-unit event-related rate changes. Zero denotes the selected event. Association does not establish causation.', 'a：点阵每行一个事件；b：PSTH显示事件附近的平均放电和标准误；c：热图显示相对基线的变化；d：各单元的放电变化。不能据此断言因果。'),
    'statistics': ('Effect sizes and statistical uncertainty', '(a) Per-unit baseline-to-response differences and bootstrap 95% intervals. (b) Raw permutation p values and BH-adjusted q values. Units and events from one session do not provide independent animal replication.', 'a：效应大小及置信区间；b：原始P值与多重比较校正。一个session的多个细胞不等于多只动物。'),
    'raw_qc': ('Signal quality', 'QC of the inspected raw-signal interval, not certification of the entire recording. Consult provenance for the actual scope.', '原始信号的噪声、饱和等诊断；局部抽检不代表整段记录均合格。'),
    'unit_qc': ('Candidate-unit quality', 'Candidate-unit quality metrics and waveform diagnostics. Automated flags support, but do not replace, manual curation.', '候选unit的质量指标与波形；自动标记不能替代人工复核。'),
    'spike_train_statistics': ('Spike-train statistics', 'Firing rates, interval variability and event-window count variability. Rate, regularity and event variability describe different properties.', '放电率、间隔规律性、事件间变异描述的是不同特征，不能混为单一质量分数。'),
    'spike_train_relationships': ('Spike-train relationships', 'Correlation and timing similarity describe statistical relationships, not anatomical connections. Distance calculations may use a bounded interval and subset of units; see provenance.', '相关和时序相似不等于解剖连接。部分距离计算只用限定时段和单元子集，范围见记录。'),
    'lfp_psd': ('Low-frequency power', 'Power spectral density of the selected low-frequency signal segment. Filtering and inspected channels constrain interpretation.', '选定低频片段的功率谱；受采集滤波、分析时段与通道选择限制。'),
    'lfp_coherence': ('Low-frequency coherence', 'Frequency-dependent statistical coupling of selected signals. Shared reference and volume conduction can contribute.', '选定信号在不同频率的相干性；共同参考和容积传导也可产生相干。'),
    'lfp_spectrogram': ('Time-frequency power', 'Spectral power over the analyzed time window; this is not necessarily the full-session spectrogram.', '分析窗口内频率能量的时间变化，不一定覆盖整段记录。'),
    'spike_field_coupling': ('Spike-field coupling', 'Phase association and surrogate comparisons under the configured frequency and time selections; not evidence of causation.', '指定频段与时段内的相位关联及替代检验，不是因果证据。'),
}


def write_publication_report(state, output: Path, figure_names: list[str]) -> Path:
    folder = output / 'publication'
    folder.mkdir(parents=True, exist_ok=True)
    inventory = []
    for path in sorted(output.rglob('*')):
        if not path.is_file() or folder in path.parents:
            continue
        relative = path.relative_to(output).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        inventory.append({'path': relative, 'bytes': path.stat().st_size, 'sha256': digest,
            'role': 'main' if path.parent.name == 'figures' and path.stem in MAIN and path.stem in figure_names else 'supplementary',
            'current_figure': path.parent.name == 'figures' and path.stem in figure_names})
    groups = [(name, 'main') for name in MAIN if name in figure_names]
    groups += [(name, 'supplementary') for name in figure_names if name not in MAIN]
    chunks = []
    legends = ['# Figure legends — author review required', '',
        'Organization follows measurement → event response → statistical evidence. No panel is selected or removed based on significance. These are descriptive drafts, not a manuscript conclusion.', '']
    guide = ['# 如何阅读本次分析', '',
        '先看质量控制，再看行为与神经活动的时间关系，最后看效应大小和不确定性。没有完成的分析不自动补结果。', '']
    guide += ['## 本次结果概况', '',
        f'- 记录时长：{state.duration_seconds:.2f}秒；通道数：{state.channel_count}。',
        f'- 当前候选单元：{len(state.sorted_spikes)}个。候选不等于已人工认定的单细胞。',
        f'- 当前分析选入事件：{state.analysis.get("selected_event_count", 0)}个。每行事件不自动等于一个独立试次。', '']
    if state.analysis:
        guide += [f'分析窗口：{state.analysis.get("window")}秒；分箱：{state.analysis.get("bin_size")}秒。', '']
    screen = state.metadata.get('automated_qc_screen')
    if screen:
        guide += ['## 质量筛选范围', '',
            '这是单独的自动质量筛选分支，不是人工确认的single-unit结果。筛选依据为质量指标，不依据事件显著性。', '',
            f'阈值：{screen["thresholds"]}。',
            f'保留Unit：{screen["included_units"]}；排除Unit：{screen["excluded_units"]}。',
            f'完整未筛选项目：{screen["source_project"]}。', '']
    if state.statistics.get('rows'):
        rows = state.statistics['rows']
        significant = [r for r in rows if r.get('significant_fdr')]
        positive = sum(r['effect_hz'] > 0 for r in significant)
        negative = sum(r['effect_hz'] < 0 for r in significant)
        guide += [f'置换检验经BH-FDR校正后，{len(significant)}/{len(rows)}个单元达到设定阈值（α={state.statistics.get("alpha", 0.05)}），其中增强{positive}个、减弱{negative}个。', '',
            '这表示在当前事件、时间窗口与假设下存在统计关联，不能解释为所有单元都有响应，也不能证明事件引起了放电。未显著不等于没有效应。', '',
            '注意：事件概览面板采用Wilcoxon检验，统计套件面板采用配对置换检验；两者结果可能不同，不应混用P值或只挑显著的一种。跨多个事件的检验还需额外考虑多重比较。', '']
    if state.source_type in ('simulated', 'benchmark_binary') or state.metadata.get('source_metadata', {}).get('benchmark_schema_version'):
        guide += ['本项目为模拟数据：这里验证的是算法与流程表现，不是新的生物学发现。真实单元恢复率应另查独立ground truth评估，不能仅凭PSTH好看判断分选正确。', '']
    counters = {'main': 0, 'supplementary': 0}
    for name, role in groups:
        counters[role] += 1
        number = str(counters[role]) if role == 'main' else 'S' + str(counters[role])
        title, caption, explanation = CAPTIONS.get(name, (name.replace('_', ' ').title(),
            'Output of the named analysis. Review the methods, scope and source table before interpretation.',
            '该分析已导出；需要结合方法参数和源数据表审核。'))
        label = f'Figure {number}'
        legends += [f'## {label}. {title}', '', caption, '',
            'Panel-specific interpretation / author additions: ____________________', '']
        guide += [f'## {label}：{name}', '', explanation, '',
            f'英文图：../figures/{name}.svg', '']
        chunks.append(f'<section><h2>{html.escape(label + ". " + title)}</h2><img src="../figures/{name}.svg" alt="{html.escape(title)}"><p>{html.escape(caption)}</p><p class="note">Author interpretation: ____________________</p></section>')
    links = ''.join(f'<li><a href="../{html.escape(item["path"], quote=True)}">{html.escape(item["path"])}</a> ({item["role"]})</li>' for item in inventory)
    document = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Analysis figure report</title>'
        '<style>body{font:15px Arial,sans-serif;color:#222;max-width:1050px;margin:40px auto;padding:0 24px;background:white}h1,h2{font-weight:600}section{margin:36px 0;break-inside:avoid}img{width:100%;height:auto}p{line-height:1.6}.note{color:#666}a{color:#654c80}@media print{body{margin:0}section{break-before:page}}</style>'
        f'<h1>{html.escape(state.name)}</h1><p>English analysis figures and supplementary evidence. Draft organization; scientific review and target-journal checks remain required.</p>'
        '<p>Main figures follow behavioral context, neural response and statistical uncertainty. All remaining artifacts are indexed below, including alternative formats and prior files. No significance-based filtering is applied.</p>'
        + ''.join(chunks) + '<h2>Complete artifact inventory</h2><ul>' + links + '</ul></html>')
    (folder / 'index.html').write_text(document, encoding='utf-8')
    (folder / 'figure_legends.md').write_text('\n'.join(legends), encoding='utf-8')
    (folder / '结果阅读说明.md').write_text('\n'.join(guide), encoding='utf-8')
    (folder / 'artifact_inventory.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
    return folder / 'index.html'
