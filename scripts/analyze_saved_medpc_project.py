"""Analyze each confirmed MED-PC event separately; keep all candidate QC visible."""
import argparse
import json
import sys
from copy import deepcopy
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
    parser.add_argument('--qc-screen', action='store_true', help='Create a separate conservative automated-screen project; not manual acceptance')
    parser.add_argument('--max-isi-violation', type=float, default=0.01)
    parser.add_argument('--min-snr', type=float, default=5.0)
    parser.add_argument('--min-spikes', type=int, default=500)
    args = parser.parse_args()
    state = load_project(args.project)
    if not state.sorted_spikes:
        raise ValueError('Run an actual sorter first')
    if args.qc_screen:
        source_manifest = state.root / 'neuroflow_project.json'
        state = deepcopy(state)
        accepted = {int(row['unit_id']) for row in state.unit_metrics
                    if row['isi_violation_rate'] <= args.max_isi_violation
                    and row['snr'] >= args.min_snr and row['spike_count'] >= args.min_spikes}
        screening = {'source_project': str(source_manifest),
                     'status': 'automated screen only; manual review outstanding',
                     'thresholds': {'max_isi_violation': args.max_isi_violation, 'min_snr': args.min_snr, 'min_spikes': args.min_spikes},
                     'included_units': sorted(accepted), 'excluded_units': sorted(set(state.sorted_spikes) - accepted)}
        state.root = state.root / 'screened_review'
        state.root.mkdir(parents=True, exist_ok=True)
        (state.root / 'screening_decisions.json').write_text(json.dumps(screening, indent=2), encoding='utf-8')
        if not accepted:
            print('No units passed this automated screen; no inferential plots generated', flush=True)
            return
        state.sorted_spikes = {u:t for u,t in state.sorted_spikes.items() if u in accepted}
        state.unit_metrics = [r for r in state.unit_metrics if r['unit_id'] in accepted]
        state.unit_diagnostics = {u:d for u,d in state.unit_diagnostics.items() if u in accepted}
        state.active_sorter_key = 'automated_qc_screen'
        state.sorting_results = {state.active_sorter_key: state.sorted_spikes}
        state.metadata['automated_qc_screen'] = screening
        state.name += ' - automated QC screen, not manually curated'
        state.analysis = {}
        state.statistics = {}
        save_project(state)
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
                'scope': ('Automated QC-screen subset, not manually curated' if args.qc_screen else 'All candidate units, not manually accepted single cells') + '; FDR within event only', 'output': str(output)})
            print(json.dumps(summaries[-1], ensure_ascii=False), flush=True)
    finally:
        state.events = original
        save_project(state)
        (state.root / 'exports/event_analysis_summary.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
