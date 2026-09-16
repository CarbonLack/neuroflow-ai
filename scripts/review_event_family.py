"""Audit the full exported event-by-unit test family without changing original tests."""
import argparse
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from neuroflow.statistics import adjust_pvalues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    rows = []
    reports = []
    for path in sorted((args.project / 'exports').glob('event_*/provenance.json')):
        result = json.loads(path.read_text(encoding='utf-8'))
        reports.append(path.parent.name)
        for row in result.get('statistics', {}).get('rows', []):
            rows.append({'event': path.parent.name, 'unit_id': row['unit_id'],
                         'permutation_p': row['permutation_p'], 'within_event_q': row['fdr_q'],
                         'effect_hz': row['effect_hz'], 'n_events': row['n_trials']})
    if not rows:
        raise ValueError('No exported event tests found')
    p = np.asarray([r['permutation_p'] for r in rows], dtype=float)
    finite = np.isfinite(p)
    q = np.full(len(p), np.nan)
    q[finite] = adjust_pvalues(p[finite], 'fdr_bh')
    for row, value in zip(rows, q):
        row['across_event_unit_q'] = float(value) if np.isfinite(value) else None
        row['significant_across_event_unit_family'] = bool(value < .05)
    output = args.project / 'exports' / 'event_family_review'
    output.mkdir(exist_ok=True)
    payload = {'scope': 'All exported event-by-unit permutation tests within this sorter project; not across sorters or animals',
               'alpha': .05, 'method': 'Benjamini-Hochberg', 'tested_count': int(finite.sum()),
               'significant_test_count': sum(r['significant_across_event_unit_family'] for r in rows), 'rows': rows}
    (output / 'event_family_tests.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    links = ''.join(f'<li><a href="../{html.escape(name)}/publication/index.html">{html.escape(name)}</a></li>' for name in reports)
    table = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(r[k]))}</td>' for k in
                    ('event', 'unit_id', 'n_events', 'effect_hz', 'within_event_q', 'across_event_unit_q')) + '</tr>' for r in rows)
    page = '<!doctype html><html lang="zh"><meta charset="utf-8"><title>跨事件统计复核</title><style>body{font:15px Arial,sans-serif;max-width:1150px;margin:32px auto;padding:20px;color:#222}td,th{padding:8px;border-bottom:1px solid #ddd}table{border-collapse:collapse}a{color:#705780}</style>'
    page += f'<h1>跨事件统计复核</h1><p>共检验 {payload["tested_count"]} 个事件×单元组合；全家族BH校正后 {payload["significant_test_count"]} 个组合达到q&lt;0.05。这个数量不是独立神经元数，也不是动物数。</p>'
    page += '<p>原报告按每种事件分别校正。本补充把已导出的全部事件与单元同时纳入校正，不覆盖原始检验，不挑选显著图。仅限当前工具/筛选项目，不将多工具结果当作独立重复。</p><p>候选簇必须先经质量复核；统计显著不能挽救不合格分选。自动筛选不是人工验收，事件相互重叠、行为连续性和单只动物的局限仍存在。</p>'
    page += '<h2>所有事件报告</h2><ul>' + links + '</ul><h2>完整检验表</h2><table><tr><th>Event</th><th>Unit</th><th>Events</th><th>Effect (Hz)</th><th>Within-event q</th><th>Across-event q</th></tr>' + table + '</table></html>'
    (output / 'index.html').write_text(page, encoding='utf-8')
    print(output / 'index.html', flush=True)


if __name__ == '__main__':
    main()
