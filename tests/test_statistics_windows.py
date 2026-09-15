import numpy as np
from neuroflow.models import ProjectState
from neuroflow.statistics import run_statistical_suite


def test_statistics_respects_selected_alignment_windows(tmp_path):
    state = ProjectState(root=tmp_path)
    state.analysis = {
        'baseline_window': [-1, -.5], 'response_window': [.5, 1],
        'bin_centers': np.array([-.75, -.25, .25, .75]),
        'conditions': ['all'] * 5,
        'units': {0: {'rates': np.tile([1., 10., 20., 5.], (5,1))}},
    }
    result = run_statistical_suite(state)
    assert result['rows'][0]['effect_hz'] == 4
    assert result['baseline_window'] == [-1, -.5]
    assert result['response_window'] == [.5, 1]
