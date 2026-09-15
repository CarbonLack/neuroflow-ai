"""Analyze each confirmed MED-PC event separately; keep all candidate QC visible."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use('Agg')
from neuroflow.project import load_project, save_project
from neuroflow.analysis import event_aligned_analysis, export_reproducible_bundle
from neuroflow.statistics import run_statistical_suite
from neuroflow.medpc import CONFIRMED_EVENT_DICTIONARY


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    state = load_project(args.project)
    if not state.sorted_spikes:
        raise ValueError('Run an actual sorter first')
    original = state.events
    summaries = []
    try:
        for code in (1, 3, 5, 7, 17, 19, 21, 22):
            selected = [e for e in original if e.get('event_code') == code]
            if len(selected) < 3:
                summaries.append({'event_code': code, 'status': 'insufficient events', 'count': len(selected)})
                continue
            state.events = selected
            event_aligned_analysis(state)
            run_statistical_suite(state)
            name = CONFIRMED_EVENT_DICTIONARY[code]['label']
            output = state.root / 'exports' / f'event_{code:02d}_{name}'
            export_reproducible_bundle(state, output)
            summaries.append({'event_code': code, 'event_name': name, 'selected_count': state.analysis['selected_event_count'],
                'units': len(state.sorted_spikes), 'significant_units_bh_fdr': state.statistics['significant_count'],
                'scope': 'All candidate units, not manually accepted single cells; FDR within event only', 'output': str(output)})
            print(json.dumps(summaries[-1], ensure_ascii=False), flush=True)
    finally:
        state.events = original
        save_project(state)
        (state.root / 'exports/event_analysis_summary.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
