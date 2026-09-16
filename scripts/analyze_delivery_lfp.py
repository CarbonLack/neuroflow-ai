"""Explicitly scoped low-frequency checks; never infer missing acquisition bands."""
import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use('Agg')
import numpy as np
from neuroflow.project import load_project, save_project
from neuroflow.ephys_toolkit import run_lfp_suite, run_spike_field_suite
from neuroflow.analysis import export_reproducible_bundle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True, type=Path)
    args = parser.parse_args()
    state = deepcopy(load_project(args.project))
    source = str(state.root / 'neuroflow_project.json')
    state.root = state.root / 'low_frequency_review'
    state.name += ' - first 30 s exploratory low-frequency review'
    state.analysis = {}
    state.statistics = {}
    state.decoding = {}
    state.regression = {}
    state.spike_train_analysis = {}
    lfp = run_lfp_suite(state)
    coupling = run_spike_field_suite(state)
    coupling['duration_seconds'] = lfp['duration_seconds']
    # A unit absent from this excerpt has no estimable phase-locking significance.
    for row in coupling['rows']:
        if row['spike_count'] == 0:
            row['surrogate_p'] = float('nan')
    frequencies = np.asarray(lfp['frequencies_hz'])
    psd = np.asarray(lfp['psd'])
    mask = (frequencies >= 1) & (frequencies <= 100)
    peaks = [float(frequencies[mask][np.argmax(row[mask])]) for row in psd]
    scope = {'source_project': source, 'start_seconds': 0,
             'duration_seconds': lfp['duration_seconds'], 'channel_ids': lfp['channel_ids'],
             'dominant_frequency_1_to_100_hz': peaks,
             'status': 'exploratory excerpt; not a whole-session or ground-truth coupling validation'}
    state.metadata['low_frequency_review_scope'] = scope
    save_project(state)
    output = export_reproducible_bundle(state, state.root / 'exports')
    (state.root / 'scope.json').write_text(json.dumps(scope, ensure_ascii=False, indent=2), encoding='utf-8')
    (state.root / '阅读说明.md').write_text(
        '# 低频分析：限定片段的探索性检查\n\n'
        f"仅分析记录起始 {lfp['duration_seconds']:g} 秒、通道 {lfp['channel_ids']}，不是全程20分钟。\n\n"
        f'1–100 Hz 内各通道最大功率频率为 {peaks} Hz。功率谱描述能量分布，时频图描述这段时间内的变化。\n\n'
        '相干性是两个通道的频域关联，可能来自共同信号或共同参考，不能解释成因果连接。\n\n'
        'Spike–field 图考察候选单元放电相对于1–5 Hz相位的偏好；只用这30秒内的放电。'
        '循环移位检验是探索性逐单元检验，未做跨单元多重比较校正，不作为最终阳性结论。'
        'PAC数值也不是经过显著性验证的跨频耦合结论。\n\n'
        '本报告独立保存，不覆盖完整会话项目。真实实验数据已在采集时高通，不能用此流程恢复不存在的低频。\n',
        encoding='utf-8')
    print(output, flush=True)


if __name__ == '__main__':
    main()
