"""Build an App-openable comparison project from independently run sorters."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use('Agg')
from neuroflow.project import load_project, save_project
from neuroflow.sorting_results import register_sorting_result, compare_sorting_results
from neuroflow.figures import sorting_comparison_figure


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', type=Path, required=True)
    args = parser.parse_args()
    sources = [(key, load_project(args.batch / key)) for key in ('kilosort4', 'mountainsort5', 'spykingcircus2')]
    reference = sources[0][1]
    for key, source in sources:
        if not source.sorted_spikes:
            raise ValueError(f'{key} has no saved sorting result')
        if (source.source_path, source.sampling_rate, source.channel_count, source.duration_seconds) != (reference.source_path, reference.sampling_rate, reference.channel_count, reference.duration_seconds):
            raise ValueError('Sorters did not analyze the same recording scope')
    state = deepcopy(reference)
    state.root = args.batch / 'sorter_comparison'
    state.name += ' - three-sorter comparison'
    state.sorting_results = {}
    state.sorting_provenance = {}
    state.unit_metrics_by_sorter = {}
    state.unit_diagnostics_by_sorter = {}
    for key, source in sources:
        register_sorting_result(state, key, source.sorted_spikes,
            {**source.metadata.get('sorting', {}), 'source_project': str(source.root / 'neuroflow_project.json')}, activate=False)
        state.unit_metrics_by_sorter[key] = source.unit_metrics
        state.unit_diagnostics_by_sorter[key] = source.unit_diagnostics
    state.active_sorter_key = 'kilosort4'
    state.analysis = {}
    state.statistics = {}
    state.spike_train_analysis = {}
    state.decoding = {}
    state.regression = {}
    state.ground_truth = {}
    state.metadata['language'] = 'en_US'
    compare_sorting_results(state)
    save_project(state)
    output = state.root / 'exports'
    output.mkdir(exist_ok=True)
    figure = sorting_comparison_figure(state)
    figure.savefig(output / 'three_sorter_comparison.png', dpi=180, bbox_inches='tight')
    figure.savefig(output / 'three_sorter_comparison.svg', bbox_inches='tight')
    (output / '说明.md').write_text('# 三种分选结果横向对比\n\n三种算法处理同一份原始记录。可在App中切换活动分选结果，检查对应QC。\n\n一致性是算法之间的重现程度，不是真实准确率；两个算法可能共同漏检或误检。模拟数据的真实恢复率请另看独立evaluation报告。默认活动工具只是浏览入口，不表示被认定为最佳。\n', encoding='utf-8')
    print(state.root, flush=True)


if __name__ == '__main__':
    main()
