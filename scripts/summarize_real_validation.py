"""Summarize saved real-data evidence without promoting candidates to accepted units."""
import argparse
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from neuroflow.project import load_project

SORTERS = ('kilosort4', 'mountainsort5', 'spykingcircus2')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--delivery', type=Path, required=True)
    parser.add_argument(
        '--subjects',
        help='Optional comma-separated confirmed subject groups to include (for example 101,102,104).',
    )
    args = parser.parse_args()
    selected_subjects = {
        item.strip() for item in (args.subjects or '').split(',') if item.strip()
    }
    rows = []
    for subject in sorted((args.delivery / 'real').glob('subject*')):
        subject_group = subject.name.removeprefix('subject')
        if selected_subjects and subject_group not in selected_subjects:
            continue
        for sorter in SORTERS:
            root = subject / sorter
            manifest = root / 'neuroflow_project.json'
            if not manifest.exists():
                rows.append({'subject_group': subject_group, 'sorter': sorter,
                             'status': 'not_completed'})
                continue
            state = load_project(manifest)
            execution_log = root / 'execution.log'
            completed = execution_log.exists() and 'SORT AND QC COMPUTED:' in execution_log.read_text(encoding='utf-8', errors='replace')
            if not completed:
                rows.append({'subject_group': subject_group, 'sorter': sorter,
                             'status': 'in_progress', 'project': str(manifest)})
                continue
            screen_file = root / 'screened_review/screening_decisions.json'
            screen = json.loads(screen_file.read_text(encoding='utf-8')) if screen_file.exists() else {}
            event_file = root / 'exports/event_family_review/event_family_tests.json'
            event = json.loads(event_file.read_text(encoding='utf-8')) if event_file.exists() else {}
            sync = state.metadata.get('synchronization', {})
            identity = state.metadata.get('subject_identity', {})
            rows.append({'subject_group': subject_group, 'sorter': sorter,
                         'status': 'computed_empty' if not state.sorted_spikes else 'computed', 'candidate_clusters': len(state.sorted_spikes),
                         'candidate_spikes': sum(len(v) for v in state.sorted_spikes.values()),
                         'automated_screen_retained': len(screen.get('included_units', [])) if screen else None,
                         'manual_curation': 'pending', 'behavior_available': identity.get('behavior_available', bool(state.events)),
                         'source_internal_subject': identity.get('source_internal_subject'),
                         'sync_matched': sync.get('matched_count'), 'sync_mean_abs_residual_ms': sync.get('mean_abs_residual_ms'),
                         'event_unit_tests': event.get('tested_count'),
                         'significant_event_unit_tests_across_family': event.get('significant_test_count'),
                         'project': str(manifest)})
    payload = {'scope': 'Independent channel-group projects; candidate clusters are not manually accepted single units',
               'included_subject_groups': sorted(selected_subjects) if selected_subjects else 'all_discovered',
               'screen': 'ISI violation <=0.01, SNR >=5, spikes >=500 when available; automated only',
               'rows': rows}
    (args.delivery / 'real_validation_summary.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    headers = ['动物/通道组', '工具', '状态', '候选簇', '自动筛选暂留', '同步锚点', '平均残差(ms)', '跨事件显著组合']
    def value(row, key):
        item = row.get(key)
        return '—' if item is None else str(item)
    matrix = [[r['subject_group'], r['sorter'], r['status'], value(r, 'candidate_clusters'),
               value(r, 'automated_screen_retained'), value(r, 'sync_matched'),
               value(r, 'sync_mean_abs_residual_ms'), value(r, 'significant_event_unit_tests_across_family')] for r in rows]
    markdown = ['# 真实数据验证汇总', '', '候选簇不是人工确认单元；自动筛选只用于缩小复核范围。统计显著不能弥补分选质量问题。', '',
                '| ' + ' | '.join(headers) + ' |', '|' + '|'.join(['---'] * len(headers)) + '|']
    markdown += ['| ' + ' | '.join(items) + ' |' for items in matrix]
    markdown += ['', '“跨事件显著组合”是同一工具内全部事件×候选Unit共同BH校正后的组合数，不是独立神经元或动物数量。无行为组不进行该分析。',
                 '三工具一致性只表示可重复性，不是准确率；人工波形、不应期、漂移、存在性和重复Unit复核仍待完成。']
    (args.delivery / '真实数据验证汇总.md').write_text('\n'.join(markdown), encoding='utf-8')
    body = ''.join('<tr>' + ''.join(f'<td>{html.escape(x)}</td>' for x in row) + '</tr>' for row in matrix)
    page = '<!doctype html><html lang="zh"><meta charset="utf-8"><title>真实数据验证汇总</title><style>body{font:15px Arial,"Microsoft YaHei",sans-serif;max-width:1250px;margin:32px auto;padding:20px;color:#28232d}table{border-collapse:collapse;width:100%}td,th{padding:9px;border-bottom:1px solid #ddd}th{background:#eee8f2}p{line-height:1.7}</style><h1>真实数据验证汇总</h1><p>候选簇、自动筛选和人工验收是三个阶段。下表只报告已保存证据，缺失项不按零处理。</p><table><tr>' + ''.join(f'<th>{x}</th>' for x in headers) + '</tr>' + body + '</table><p>跨事件显著组合不是独立神经元或动物数。无行为组只做分选和质控。人工复核仍待完成。</p></html>'
    (args.delivery / '真实数据验证汇总.html').write_text(page, encoding='utf-8')
    # GitHub's Windows runner can expose a legacy cp1252 stdout even though the
    # generated files are UTF-8. Keep console output ASCII-only; the actual
    # Chinese filenames above remain unchanged.
    print('real validation summary written', flush=True)


if __name__ == '__main__':
    main()
