"""Accountable publication outline; never invent biological conclusions."""
from __future__ import annotations
import hashlib
import html
import json
from pathlib import Path

# Content-based grouping, never significance-based selection.
MAIN = ('behavior', 'raster_psth_population', 'statistics', 'decoding')
MAIN_STORY = (
    ("Experimental context and evidence quality", ("behavior", "raw_qc", "unit_qc")),
    ("Event-aligned and population activity", ("raster_psth_population", "spike_train_statistics", "population_dynamics")),
    ("Effect sizes, uncertainty and prediction", ("statistics", "decoding", "regression")),
)
CAPTIONS = {
    'behavior': ('Behavioral context', 'Observed event timing and available trial summaries. Event rows are not necessarily independent trials.', '行为发生的时间与已有试次信息。事件条数不等于独立试次数。'),
    'raster_psth_population': ('Event-aligned neural activity', '(a) Raster for the displayed unit, one event per row. (b) Mean PSTH, shading: SEM across available events. (c) Baseline-normalized population activity. (d) Per-unit event-related rate changes. Zero denotes the selected event. Association does not establish causation.', 'a：点阵每行一个事件；b：PSTH显示事件附近的平均放电和标准误；c：热图显示相对基线的变化；d：各单元的放电变化。不能据此断言因果。'),
    'statistics': ('Effect sizes and statistical uncertainty', '(a) Per-unit baseline-to-response differences and bootstrap 95% intervals. (b) Raw permutation p values and BH-adjusted q values. Units and events from one session do not provide independent animal replication.', 'a：效应大小及置信区间；b：原始P值与多重比较校正。一个session的多个细胞不等于多只动物。'),
    'raw_qc': ('Signal quality', 'QC of the inspected raw-signal interval, not certification of the entire recording. Consult provenance for the actual scope.', '原始信号的噪声、饱和等诊断；局部抽检不代表整段记录均合格。'),
    'preprocessing': ('Preprocessing evidence', 'Raw and processed voltage views under the recorded filter and reference settings. The source recording remains unchanged.', '处理前后电压及其滤波、参考设置；源记录保持不变。'),
    'sorting_comparison': ('Spike-sorting evidence', 'Normalized sorter outputs, agreement or simulated-ground-truth performance where available. Agreement is not biological ground truth.', '统一后的分选结果、算法一致度或可用的模拟真值表现；一致不等于生物学真值。'),
    'unit_qc': ('Candidate-unit quality', 'Candidate-unit quality metrics and waveform diagnostics. Automated flags support, but do not replace, manual curation.', '候选unit的质量指标与波形；自动标记不能替代人工复核。'),
    'synchronization': ('Behavior–electrophysiology synchronization', 'Clock mapping, residual error, missing pulses and event alignment diagnostics. Inspect residuals before event-locked inference.', '行为与电生理时钟映射、残差、漏脉冲和事件对齐诊断；事件分析前需检查残差。'),
    'spike_train_statistics': ('Spike-train statistics', 'Firing rates, interval variability and event-window count variability. Rate, regularity and event variability describe different properties.', '放电率、间隔规律性、事件间变异描述的是不同特征，不能混为单一质量分数。'),
    'spike_train_relationships': ('Spike-train relationships', 'Correlation and timing similarity describe statistical relationships, not anatomical connections. Distance calculations may use a bounded interval and subset of units; see provenance.', '相关和时序相似不等于解剖连接。部分距离计算只用限定时段和单元子集，范围见记录。'),
    'lfp_psd': ('Low-frequency power', 'Power spectral density of the selected low-frequency signal segment. Filtering and inspected channels constrain interpretation.', '选定低频片段的功率谱；受采集滤波、分析时段与通道选择限制。'),
    'lfp_coherence': ('Low-frequency coherence', 'Frequency-dependent statistical coupling of selected signals. Shared reference and volume conduction can contribute.', '选定信号在不同频率的相干性；共同参考和容积传导也可产生相干。'),
    'lfp_spectrogram': ('Time-frequency power', 'Spectral power over the analyzed time window; this is not necessarily the full-session spectrogram.', '分析窗口内频率能量的时间变化，不一定覆盖整段记录。'),
    'spike_field_coupling': ('Spike-field coupling', 'Phase association and surrogate comparisons under the configured frequency and time selections; not evidence of causation.', '指定频段与时段内的相位关联及替代检验，不是因果证据。'),
}

PANEL_CAPTIONS = {
    'behavior': [
        'Observed event counts by label; counts are not independent-trial counts.',
        'Event timestamps across the inspected session; one row per event label, not one row per animal.'],
    'raw_qc': [
        'Per-channel RMS noise in the inspected raw interval; line and shading reflect the configured screen.',
        'Primary signal-quality indicators for the inspected interval. This does not certify the full recording.'],
    'preprocessing': [
        'Raw multichannel voltage in the configured preview window.',
        'Processed preview under the stated filter and referencing choices; the source file is unchanged.'],
    'sorting_comparison': [
        'Sorter performance or normalized output size under the available validation design.',
        'Pairwise agreement of matched candidate Units; agreement is not ground truth.',
        'Candidate counts, unmatched results, or provenance summary for the compared outputs.'],
    'unit_qc': [
        'Candidate-unit firing rate versus signal-to-noise ratio; labels are automated screening flags.',
        'Refractory-period violation estimates for candidates. Human curation remains required.'],
    'synchronization': [
        'Behavior-device timestamps mapped to electrophysiology timestamps.',
        'Clock-model residuals over the recording.',
        'Event-pair interval or residual distribution used to diagnose mismatch.',
        'Matched and missing synchronization-event summary.'],
    'raster_psth_population': [
        'Example-unit event-aligned raster; each row is an event, and time zero is event onset.',
        'Condition-averaged peristimulus firing rate; bands show available-event uncertainty.',
        'Population event-response heatmap. Color encodes the plotted normalization, not an anatomical map.',
        'Per-unit post-event minus baseline firing-rate changes; units share one recording session.'],
    'population_ordered_heatmap': [
        'Population activity ordered by response timing; the order is descriptive and chosen from these data.',
        'Population mean and uncertainty around event onset; temporal association is not causality.'],
    'population_single_trial': [
        'Example single-trial population trajectory; one trial is not a population-level effect.',
        'Across-trial response summary under the configured selection and normalization.'],
    'population_conditions': [
        'Condition-by-time population response map; conditions are those available in this project.',
        'Condition-averaged response traces with uncertainty across available observations.'],
    'population_pca': [
        'Low-dimensional population trajectory from PCA; axes are mathematical components, not brain regions.',
        'Explained-variance or trajectory summary for the same population and trial selection.'],
    'statistics': [
        'Per-unit response effect sizes and bootstrap 95% intervals. Units do not substitute for animal replication.',
        'Raw permutation evidence versus FDR-adjusted evidence; all tested units remain shown.'],
    'decoding': [
        'Cross-validated confusion matrix; inspect class balance and trial grouping before interpretation.',
        'Observed decoder score against label-permutation null; p refers to this configured decoding test.',
        'ROC curve and AUC for the selected contrast; performance is conditional on the held-out design.',
        'Time-resolved decoding around event onset; avoid interpreting peak bins without multiple-time control.',
        'PCA trajectories of decoding features; separation may reflect task and recording confounds.',
        'Feature importance for the fitted model; it is not a causal contribution of a unit.'],
    'behavior_spectrum_animals': [
        'Behavioral event spectrum with one row per animal; colors identify behavior labels.'],
    'behavior_spectrum_by_behavior': [
        'One animal shown with separate rows for behavior categories; time scale is recorded in the axis.'],
    'spike_train_statistics': [
        'Firing-rate distribution across candidate units.',
        'Inter-spike interval regularity across candidates.',
        'Event-window spike-count variability.',
        'Additional spike-train diagnostic from the configured analysis window.'],
    'spike_train_relationships': [
        'Pairwise spike-train relationship summary; correlation is not connectivity.',
        'Timing-related relationship summary for selected units.',
        'Distribution of pairwise relationship values for the bounded analysis subset.',
        'Additional pairwise diagnostic; selection and time window are in provenance.'],
    'connectivity_ccg_examples': [
        'Example cross-correlogram; peaks can arise without monosynaptic connectivity.',
        'Second example cross-correlogram under the same screening rule.',
        'Third example cross-correlogram under the same screening rule.',
        'Fourth example cross-correlogram under the same screening rule.'],
    'connectivity_network': [
        'Thresholded functional relationship network, not a verified anatomical circuit.',
        'Spatial distribution of the selected functional relationships.'],
    'connectivity_distance': [
        'Functional relationship strength versus estimated probe-space distance.',
        'Distance-binned relationship summary.',
        'Additional spatial-control diagnostic for the same candidate set.'],
    'lfp_psd': [
        'Power spectral density for the selected low-frequency signal and interval.',
        'Band-power summary; acquisition filtering bounds which frequencies are interpretable.'],
    'lfp_coherence': [
        'Frequency-specific coherence of selected signals; common reference can contribute.',
        'Coherence summary under the configured channel and window selection.'],
    'lfp_spectrogram': [
        'Time-frequency power over the analyzed interval.',
        'Spectral summary over the same interval; it may not cover the whole session.'],
    'spike_field_coupling': [
        'Spike-field phase relationship under the selected frequency and event window.',
        'Surrogate or frequency-specific coupling comparison; association is not causality.'],
    'respiration_state_analysis': [
        'Respiration-state measurement in a separate method-validation branch.',
        'State-conditioned neural summary; do not merge this task with the primary decision analysis.'],
    'respiration_phase_amplitude_coupling': [
        'Respiration-phase relationship from the method-validation branch.',
        'Phase-amplitude coupling or control summary for the selected interval.'],
}


def write_publication_report(state, output: Path, figure_names: list[str]) -> Path:
    folder = output / 'publication'
    folder.mkdir(parents=True, exist_ok=True)
    from .publication_layout import write_sized_figures
    write_sized_figures(output, figure_names)
    available = list(dict.fromkeys(figure_names))
    main_names = {
        name for _, names in MAIN_STORY for name in names if name in available
    }
    inventory = []
    for path in sorted(output.rglob('*')):
        if not path.is_file() or folder in path.parents:
            continue
        relative = path.relative_to(output).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        inventory.append({'path': relative, 'bytes': path.stat().st_size, 'sha256': digest,
            'role': 'main' if path.parent.name == 'figures' and path.stem in main_names else 'supplementary',
            'current_figure': path.parent.name == 'figures' and path.stem in figure_names})
    story_groups = []
    assigned = set()
    for title, candidates in MAIN_STORY:
        names = [name for name in candidates if name in available]
        if names:
            story_groups.append({"role": "main", "title": title, "figures": names})
            assigned.update(names)
    remaining = [name for name in available if name not in assigned]
    for start in range(0, len(remaining), 4):
        names = remaining[start:start + 4]
        story_groups.append({
            "role": "supplementary",
            "title": "Supporting diagnostics and complete secondary evidence",
            "figures": names,
        })
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
    storyboard = []
    for group in story_groups:
        role = group["role"]
        counters[role] += 1
        number = str(counters[role]) if role == 'main' else 'S' + str(counters[role])
        label = f'Figure {number}'
        legends += [f'## {label}. {group["title"]}', '']
        panels = []
        panel_html = []
        for panel_index, name in enumerate(group["figures"]):
            letter = chr(ord('a') + panel_index)
            title, caption, explanation = CAPTIONS.get(name, (name.replace('_', ' ').title(),
                'Output of the named analysis. Review the methods, scope and source table before interpretation.',
                '该分析已导出；需要结合方法参数和源数据表审核。'))
            panel_label = f'{label}{letter}'
            legends += [f'**({letter}) {title}.** {caption}', '']
            guide += [f'## {panel_label}：{name}', '', explanation, '',
                f'英文图：../figures/{name}.svg', '']
            panels.append({
                'panel': letter,
                'figure_name': name,
                'title': title,
                'caption_draft': caption,
                'source_svg': f'figures/{name}.svg',
                'plotted_data': f'figure_data/{name}.json',
            })
            panel_html.append(
                f'<div class="panel"><h3>({letter}) {html.escape(title)}</h3>'
                f'<img src="../figures/{name}.svg" alt="{html.escape(title)}">'
                f'<p>{html.escape(caption)}</p></div>'
            )
        legends += ['Panel-specific interpretation / author additions: ____________________', '']
        storyboard.append({
            'figure': label,
            'role': role,
            'story_role': group['title'],
            'panels': panels,
            'author_interpretation': '',
        })
        chunks.append(
            f'<section><h2>{html.escape(label + ". " + group["title"])}</h2>'
            + ''.join(panel_html)
            + '<p class="note">Author interpretation: ____________________</p></section>'
        )
    links = ''.join(f'<li><a href="../{html.escape(item["path"], quote=True)}">{html.escape(item["path"])}</a> ({item["role"]})</li>' for item in inventory)
    event_reports = sorted(output.glob('event_*/publication/index.html'))
    companion_links = ''.join(
        f'<li><a href="../{html.escape(path.relative_to(output).as_posix(), quote=True)}">'
        f'{html.escape(path.parent.parent.name.replace("_", " "))}</a></li>'
        for path in event_reports
    )
    family_review = output / 'event_family_review' / 'index.html'
    if family_review.is_file():
        companion_links += '<li><a href="../event_family_review/index.html">Cross-event family correction</a></li>'
    companion_section = (
        '<section><h2>Companion event analyses</h2><p>Each linked report was recomputed for its own '
        'event family; the primary light-side decoder and population dynamics are not relabeled '
        'as results for other events.</p><ul>' + companion_links + '</ul></section>'
        if companion_links else ''
    )
    document = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Analysis figure report</title>'
        '<style>body{font:15px Arial,sans-serif;color:#222;max-width:1050px;margin:40px auto;padding:0 24px;background:white}h1,h2{font-weight:600}section{margin:36px 0;break-inside:avoid}.panel{margin:24px 0}.panel img{width:100%;height:auto}p{line-height:1.6}.note{color:#666}a{color:#654c80}@media print{body{margin:0}section{break-before:page}}</style>'
        f'<h1>{html.escape(state.name)}</h1><p>English analysis figures and supplementary evidence. Draft organization; scientific review and target-journal checks remain required.</p>'
        '<p>Main figures follow behavioral context, neural response and statistical uncertainty. All remaining artifacts are indexed below, including alternative formats and prior files. No significance-based filtering is applied.</p>'
        + '<p><a href="sized_figures/README.md">Physical-size artwork and checks</a> · <a href="sized_figures/layout_checks.json">Layout diagnostics</a></p>'
        + ''.join(chunks) + companion_section + '<h2>Complete artifact inventory</h2><ul>' + links + '</ul></html>')
    (folder / 'index.html').write_text(document, encoding='utf-8')
    (folder / 'figure_legends.md').write_text('\n'.join(legends), encoding='utf-8')
    (folder / '结果阅读说明.md').write_text('\n'.join(guide), encoding='utf-8')
    (folder / 'artifact_inventory.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'storyboard.json').write_text(json.dumps({
        'schema': 'neuroephys.publication-storyboard.v1',
        'policy': 'Content-based grouping; no significance-based inclusion or omission.',
        'narrative_order': ['measurement and quality', 'event-related neural evidence', 'effect size and uncertainty', 'supporting diagnostics'],
        'figures': storyboard,
        'complete_artifact_inventory': 'artifact_inventory.json',
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    return _write_composite_report(state, output, available, inventory, companion_section, guide)


def _write_composite_report(state, output: Path, available: list[str],
                            inventory: list[dict], companion_section: str,
                            guide: list[str]) -> Path:
    """Replace the former image list with real, complete multi-panel artwork."""
    from .publication_compositor import compose_publication_figures

    folder = output / 'publication'
    figures = compose_publication_figures(output, available)
    edit_file = folder / 'author_edits.json'
    author_edits = (json.loads(edit_file.read_text(encoding='utf-8'))
                    if edit_file.is_file() else {})
    legends = ['# Figure legends — author review required', '',
        'All source analyses are assigned by evidential role. Non-significant results '
        'remain present. These captions describe measurements, not biological conclusions.', '']
    sections = []
    for figure in figures:
        label = figure['figure']
        role = figure['story_role']
        legends += [f'## {label}. {role}', '']
        captions = []
        for panel in figure['panels']:
            name = panel['figure_name']
            title, caption, explanation = CAPTIONS.get(name, (
                name.replace('_', ' ').title(),
                'Review measurement, statistical scope and source data before interpretation.',
                '请根据方法、数据来源和统计边界审核该面板。'))
            panel['title'] = (panel['title'] if panel['source_axis'] else title)
            descriptions = PANEL_CAPTIONS.get(name, [])
            axis_index = int(panel.get('source_axis', 0)) - 1
            panel['caption_draft'] = (descriptions[axis_index]
                                      if 0 <= axis_index < len(descriptions)
                                      else caption)
            panel['caption_draft'] = author_edits.get(label, {}).get(
                'captions', {}).get(panel['source_panel_svg'], panel['caption_draft'])
            panel['source_svg'] = f'figures/{name}.svg'
            legends += [f"**({panel['panel']}) {panel['title']}.** {panel['caption_draft']}",
                        f"Source: {panel['source_panel_svg']}; plotted data: "
                        f"{panel['plotted_data']}; source axis: {panel['source_axis']}.", '']
            captions.append(f"<p><b>({panel['panel']}) {html.escape(panel['title'])}.</b> "
                            f"{html.escape(panel['caption_draft'])}</p>")
            guide += [f"## {label}{panel['panel']}：{name}", '', explanation, '',
                      f"完整图：../{figure['composite_svg']}",
                      f"作图数据：../{panel['plotted_data']}", '']
        legends += ['Author interpretation and target-journal edit: ____________________', '']
        relative_svg = figure['composite_svg'].removeprefix('publication/')
        sections.append('<section>'
            f"<h2>{html.escape(label)}. {html.escape(role)}</h2>"
            f"<img src=\"{html.escape(relative_svg, quote=True)}\" "
            f"alt=\"{html.escape(label)} composite figure\">"
            + ''.join(captions) +
            '<p class="note">Interpretation requires author review; see Methods and provenance.</p>'
            '</section>')
    inventory.extend({
        'path': figure[key], 'bytes': (output / figure[key]).stat().st_size,
        'sha256': hashlib.sha256((output / figure[key]).read_bytes()).hexdigest(),
        'role': figure['role'], 'current_figure': True}
        for figure in figures for key in ('composite_svg', 'composite_png', 'composite_pdf'))
    links = ''.join(f'<li><a href="../{html.escape(item["path"], quote=True)}">'
                    f'{html.escape(item["path"])}</a></li>' for item in inventory)
    document = ('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<title>Publication figures</title><style>body{font:14px Arial,sans-serif;'
        'color:#20222a;max-width:1050px;margin:36px auto;padding:0 22px;background:white}'
        'section{margin:36px 0;break-inside:avoid}section img{display:block;width:100%;'
        'max-width:760px;height:auto;margin:20px auto}p{line-height:1.5}.note{color:#666}'
        'a{color:#624987}@media print{section{break-before:page}}</style>'
        f'<h1>{html.escape(state.name)}</h1>'
        '<p>English, multi-panel main and Extended Data figures. Scientific and '
        'journal-specific review is still required. Every exported analysis is included, '
        'regardless of statistical significance.</p>'
        + ''.join(sections) + companion_section +
        '<h2>Complete artifact inventory</h2><ul>' + links + '</ul></html>')
    (folder / 'index.html').write_text(document, encoding='utf-8')
    (folder / 'figure_legends.md').write_text('\n'.join(legends), encoding='utf-8')
    (folder / '结果阅读说明.md').write_text('\n'.join(guide), encoding='utf-8')
    (folder / 'artifact_inventory.json').write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'layout_checks.json').write_text(json.dumps({
        'profile': 'Conservative Nature double-column starting geometry',
        'scope': 'Geometry and vector generation only; not journal acceptance.',
        'max_width_mm': 183, 'max_height_mm': 170,
        'figures': [{
            'figure': item['figure'],
            'width_mm': round(item['layout']['width_pt'] * 25.4 / 72, 2),
            'height_mm': round(item['layout']['height_pt'] * 25.4 / 72, 2),
            'within_starting_geometry': (
                item['layout']['width_pt'] * 25.4 / 72 <= 183 and
                item['layout']['height_pt'] * 25.4 / 72 <= 170),
            'vector_svg': item['composite_svg'],
            'vector_pdf': item['composite_pdf'],
        } for item in figures],
        'manual_checks': ['legibility at final size', 'embedded heatmap/raster DPI',
                          'color and grayscale accessibility',
                          'correct labels and uncertainty', 'target journal format',
                          'scientific interpretation and authorship'],
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'storyboard.json').write_text(json.dumps({
        'schema': 'neuroephys.publication-storyboard.v2',
        'policy': 'Content-based grouping; all exported plots retained regardless of significance.',
        'narrative_order': ['measurement and quality', 'event and behavior',
                            'unit and population response', 'uncertainty and prediction',
                            'complete extended data'],
        'figures': figures,
        'complete_artifact_inventory': 'artifact_inventory.json',
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'README.txt').write_text(
        'PUBLICATION FIGURES / 论文组合图\n\n'
        'figures/ contains one actual multi-panel SVG, PDF and PNG per main or '
        'Extended Data Figure. PNG is for preview; SVG and PDF preserve vector paths.\n'
        'storyboard.json maps every panel to its source axis and plotted-data index.\n'
        'figure_legends.md contains editable English caption drafts.\n'
        'layout_checks.json records print-size geometry and remaining author checks.\n'
        'author_edits.json preserves panel order and captions changed in the App.\n'
        '../panels/ contains the original per-axis vector panels.\n'
        '../figure_data/ contains the plotted numeric arrays and traceability indexes.\n'
        '../provenance.json records source and workflow context.\n\n'
        'The layout includes all exported analyses, including non-significant results. '
        'It is an author-review draft, not a biological conclusion or a guarantee '
        'of acceptance by Nature, Cell, Science, or another journal.\n',
        encoding='utf-8')
    return folder / 'index.html'
