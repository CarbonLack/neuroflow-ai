import json
import numpy as np
from neuroflow.models import ProjectState
from neuroflow.analysis import export_reproducible_bundle, event_aligned_analysis


def test_export_does_not_claim_unrun_analysis(tmp_path):
    state = ProjectState(root=tmp_path, name='Actual experiment')
    state.metadata['language'] = 'zh_CN'
    output = export_reproducible_bundle(state, tmp_path / 'export')
    workflow = json.loads((output / 'workflow.json').read_text(encoding='utf-8'))
    methods = (output / 'methods.md').read_text(encoding='utf-8')
    assert workflow['project'] == 'Actual experiment'
    assert workflow['steps'] == []
    assert 'No spike-sorting results' in methods
    assert 'Trial labels were decoded' not in methods
    assert 'Spikes were aligned' not in methods
    assert state.metadata['language'] == 'zh_CN'
    assert (output / 'publication/index.html').exists()
    inventory = json.loads((output / 'publication/artifact_inventory.json').read_text(encoding='utf-8'))
    assert 'workflow.json' in {item['path'] for item in inventory}
    assert all(len(item['sha256']) == 64 for item in inventory)


def test_export_uses_actual_alignment_parameters(tmp_path):
    state = ProjectState(root=tmp_path, name='Changed window')
    state.duration_seconds = 10
    state.sorted_spikes = {0: np.array([1.9, 2.1, 4.2, 6.1])}
    state.events = [{'time_seconds': t, 'event_type': 'press'} for t in (2, 4, 6)]
    event_aligned_analysis(state, window=(-1, 2), bin_size=0.05)
    output = export_reproducible_bundle(state, tmp_path / 'export')
    methods = (output / 'methods.md').read_text(encoding='utf-8')
    assert '(-1, 2)' in methods or '[-1, 2]' in methods
    assert '0.05 s bins' in methods
