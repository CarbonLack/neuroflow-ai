import csv
import numpy as np
from neuroflow.data_import import inspect_binary_sidecars


def test_probe_local_coordinates_keep_probe_identity(tmp_path):
    with (tmp_path / 'channel_geometry.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['channel_id', 'probe_id', 'x_position_um', 'y_position_um'])
        writer.writerows([[0,'A',0,0],[1,'A',0,20],[2,'B',0,0],[3,'B',0,20]])
    result = inspect_binary_sidecars(tmp_path / 'recording.bin')
    positions = np.asarray(result['contact_positions_um'])
    assert len(np.unique(positions, axis=0)) == 4
    assert result['contact_shank_ids'] == [0,0,1,1]
    assert np.allclose(positions[1] - positions[0], [0,20])
    assert 'NOT anatomical' in result['geometry_embedding_note']
