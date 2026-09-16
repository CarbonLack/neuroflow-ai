"""Evaluate saved sorter outputs without exposing truth to sorting projects."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from neuroflow.project import load_project
from neuroflow.benchmark.sorting_evaluator import evaluate_candidate_sorting, write_sorting_evaluation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--delivery', type=Path, required=True)
    parser.add_argument('--benchmark', type=Path, required=True)
    args = parser.parse_args()
    summaries = []
    for electrode in ('tetrode', 'neuropixels'):
        for manifest in sorted((args.delivery / electrode).glob('*/neuroflow_project.json')):
            if manifest.parent.name not in ('kilosort4', 'mountainsort5', 'spykingcircus2'):
                continue
            state = load_project(manifest)
            if not state.sorted_spikes:
                continue
            output = manifest.parent / 'evaluation'
            candidate = output / 'candidate_snapshot'
            candidate.mkdir(parents=True, exist_ok=True)
            times = np.concatenate([np.asarray(t) for t in state.sorted_spikes.values()])
            clusters = np.concatenate([np.full(len(t), int(u), dtype=np.int64) for u,t in state.sorted_spikes.items()])
            order = np.argsort(times)
            np.save(candidate / 'spike_times.npy', np.rint(times[order] * state.sampling_rate).astype(np.int64))
            np.save(candidate / 'spike_clusters.npy', clusters[order])
            result = evaluate_candidate_sorting(args.benchmark / 'full/ground_truth' / electrode / 'session_01/true_spike_times.npz', candidate, state.sampling_rate)
            result['source_project'] = str(manifest)
            write_sorting_evaluation(result, output)
            row = {k:v for k,v in result.items() if k not in ('matched_pairs',)}
            row.update(electrode=electrode, sorter=manifest.parent.name)
            summaries.append(row)
            print(electrode, manifest.parent.name, 'F1', round(result['median_f1'],4), 'all-unit recall', round(result['mean_recall_all_true_units'],4), flush=True)
    (args.delivery / 'sorting_evaluation_summary.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 三种分选工具的独立评估', '', '只评估已保存的实际分选结果；未完成的工具不出现在本表。模拟真值未输入分选算法。', '',
        '| 数据 | 分选工具 | 真实单元数 | 候选簇数 | 配对中位F1 | 全体真实单元平均召回率 | F1≥0.8单元数 |', '|---|---|---:|---:|---:|---:|---:|']
    for row in summaries:
        lines.append(f"| {row['electrode']} | {row['sorter']} | {row['true_unit_count']} | {row['candidate_cluster_count']} | {row['median_f1']:.3f} | {row['mean_recall_all_true_units']:.3f} | {row['well_recovered_f1_ge_0_8']} |")
    lines += ['', 'F1综合反映误检和漏检。配对中位数可能掩盖漏掉的神经元，必须结合全体召回率和恢复单元数看。候选簇数多不等于质量好，可能有拆分或噪声簇。', '',
        '匹配采用0.4毫秒容差与一对一时间匹配，再进行单元配对。这是模拟基准评估，不等同真实实验的准确率，也不代表人工复核完成。']
    (args.delivery / '分选评估汇总.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
