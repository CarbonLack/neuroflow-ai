import json
import subprocess
import sys
from pathlib import Path


def test_summary_keeps_missing_sorters_distinct_from_zero(tmp_path):
    (tmp_path / 'real/subject102').mkdir(parents=True)
    script = Path(__file__).resolve().parents[1] / 'scripts/summarize_real_validation.py'
    subprocess.run([sys.executable, str(script), '--delivery', str(tmp_path)], check=True)
    report = json.loads((tmp_path / 'real_validation_summary.json').read_text(encoding='utf-8'))
    assert len(report['rows']) == 3
    assert all(row['status'] == 'not_completed' for row in report['rows'])
    assert all('candidate_clusters' not in row for row in report['rows'])


def test_saved_project_without_completion_marker_is_in_progress(tmp_path):
    root = tmp_path / 'real/subject102/kilosort4'
    root.mkdir(parents=True)
    (root / 'neuroflow_project.json').write_text('{"schema_version": 5, "application": "NeuroEphys AI", "name": "x", "data_type": "none", "root": ".", "sampling_rate": 30000, "channel_count": 0, "duration_seconds": 0, "dtype": "int16", "scale_uv_per_bit": 1, "events": [], "trials": [], "metadata": {}}', encoding='utf-8')
    script = Path(__file__).resolve().parents[1] / 'scripts/summarize_real_validation.py'
    subprocess.run([sys.executable, str(script), '--delivery', str(tmp_path)], check=True)
    report = json.loads((tmp_path / 'real_validation_summary.json').read_text(encoding='utf-8'))
    row = next(r for r in report['rows'] if r['sorter'] == 'kilosort4')
    assert row['status'] == 'in_progress'
    assert 'candidate_clusters' not in row
