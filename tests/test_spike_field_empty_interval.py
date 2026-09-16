import numpy as np
import neo
import quantities as pq

from neuroflow import ephys_toolkit as toolkit
from neuroflow.models import ProjectState


def test_unit_without_spikes_in_excerpt_is_not_significant(tmp_path, monkeypatch):
    state = ProjectState(name='test', root=tmp_path)
    state.sorted_spikes = {0: np.array([35.0]), 1: np.array([1.0, 2.0])}
    fs = 1000
    analog = neo.AnalogSignal(np.sin(2 * np.pi * 2 * np.arange(5000) / fs),
                              units=pq.uV, sampling_rate=fs * pq.Hz)
    monkeypatch.setattr(toolkit, 'to_neo_analog_signal', lambda state: (analog, [0]))
    monkeypatch.setattr(toolkit, 'to_neo_spike_trains', lambda state: (
        [0, 1], [neo.SpikeTrain([35.0] * pq.s, t_stop=40 * pq.s),
                 neo.SpikeTrain([1.0, 2.0] * pq.s, t_stop=40 * pq.s)]))
    result = toolkit.run_spike_field_suite(state, surrogate_count=5)
    assert result['duration_seconds'] == 5
    row = result['rows'][0]
    assert row['spike_count'] == 0
    assert np.isnan(row['surrogate_p'])
    assert np.isnan(row['vector_strength'])
    assert result['rows'][1]['spike_count'] == 2
