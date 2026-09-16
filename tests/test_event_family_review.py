import json
import subprocess
import sys
from pathlib import Path


def test_all_events_are_included_without_overwriting_original(tmp_path):
    for name, p in [('event_01_first', .01), ('event_02_second', .2)]:
        folder = tmp_path / 'exports' / name
        folder.mkdir(parents=True)
        payload = {'statistics': {'rows': [{'unit_id': 7, 'permutation_p': p,
                    'fdr_q': p, 'effect_hz': 2, 'n_trials': 10}]}}
        (folder / 'provenance.json').write_text(json.dumps(payload), encoding='utf-8')
    script = Path(__file__).resolve().parents[1] / 'scripts/review_event_family.py'
    subprocess.run([sys.executable, str(script), '--project', str(tmp_path)], check=True)
    report = json.loads((tmp_path / 'exports/event_family_review/event_family_tests.json').read_text())
    assert report['tested_count'] == 2
    assert report['rows'][0]['across_event_unit_q'] == .02
    original = json.loads((tmp_path / 'exports/event_01_first/provenance.json').read_text())
    assert original['statistics']['rows'][0]['fdr_q'] == .01
