import json
import subprocess
import sys
from pathlib import Path


def test_figure_audit_detects_non_english_and_missing_png(tmp_path):
    folder = tmp_path / 'exports' / 'x' / 'figures'
    folder.mkdir(parents=True)
    (folder / 'a.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><text>中文</text></svg>', encoding='utf-8')
    script = Path(__file__).resolve().parents[1] / 'scripts/audit_exported_figures.py'
    subprocess.run([sys.executable, str(script), '--delivery', str(tmp_path)], check=True)
    report = json.loads((tmp_path / 'figure_integrity_audit.json').read_text(encoding='utf-8'))
    assert report['figure_count'] == 1
    assert report['flagged_count'] == 1
    assert set(report['figures'][0]['checks']) == {'non_english_text', 'missing_or_empty_png'}
