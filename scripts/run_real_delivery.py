"""Read-only Open Ephys import and full-session sorting with MED-PC events."""
import argparse
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from neuroflow.data_import import import_device_recording
from neuroflow.medpc import import_medpc_behavior, parse_medpc_file
from neuroflow.project import save_project, load_project
from neuroflow.analysis import run_raw_qc, compute_unit_metrics, export_reproducible_bundle
from neuroflow.sorting import run_sorter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--recording', type=Path, required=True)
    behavior_group = parser.add_mutually_exclusive_group(required=True)
    behavior_group.add_argument('--behavior', type=Path)
    behavior_group.add_argument('--no-behavior', action='store_true', help='Explicit electrophysiology-only project; no inferred animal/event pairing')
    parser.add_argument('--confirmed-internal-subject', help='Exact documented MED identifier when the user has confirmed an alias')
    parser.add_argument('--identity-note', help='Required explanation for a confirmed identity alias')
    parser.add_argument('--channels', required=True, help='Confirmed one-animal acquisition channel selection')
    parser.add_argument('--subject', required=True)
    parser.add_argument('--ttl-channel', type=int)
    parser.add_argument('--highpass-hz', type=float, default=0)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sorter', required=True)
    parser.add_argument('--sorter-settings', type=Path, help='Optional JSON parameters, preserved in sorting provenance')
    parser.add_argument('--attempt', default='', help='Separate result-folder suffix; preserves failed attempts')
    args = parser.parse_args()
    if args.behavior and args.ttl_channel is None:
        parser.error('--ttl-channel is required with behavior')
    args.output.mkdir(parents=True, exist_ok=True)
    def log(message):
        line = f'{datetime.now().isoformat(timespec="seconds")} {message}'
        print(line, flush=True)
        with (args.output / 'execution.log').open('a', encoding='utf-8') as stream:
            stream.write(line + '\n')
    try:
        manifest = args.output / 'neuroflow_project.json'
        if manifest.exists():
            state = load_project(manifest)
        else:
            declared_subject = parse_medpc_file(args.behavior).metadata.get('Subject') if args.behavior else None
            if declared_subject and declared_subject != args.subject:
                if args.confirmed_internal_subject != declared_subject or not args.identity_note:
                    raise ValueError(f'MED-PC internal Subject {declared_subject} does not match selected subject {args.subject}; resolve identity before analysis')
            log(f'IMPORT subject {args.subject}, acquisition channels {args.channels}; source unchanged')
            state = import_device_recording(args.output,
                args.recording, 'Open Ephys', channel_selection=args.channels)
            state.name = f'Subject {args.subject} full session - {args.sorter}'
            state.metadata['language'] = 'en_US'
            state.metadata['subject_identity'] = {
                'selected_subject': args.subject, 'source_internal_subject': declared_subject,
                'confirmation_note': args.identity_note,
                'behavior_available': bool(args.behavior)}
            state.metadata['probe'] = {'geometry_mode': 'independent_contacts',
                'geometry_note': 'Physical microwire positions unknown. Algorithmic separated contacts are NOT measured geometry. Cross-contact duplicate-unit review required.'}
            if args.highpass_hz >= 30:
                state.metadata.setdefault('acquisition_preprocessing', {}).update({
                    'lfp_available': False,
                    'lfp_unavailable_reason': f'User-declared acquisition high-pass at {args.highpass_hz} Hz; low-frequency signal unavailable.'})
            state.metadata['delivery_constraints'] = {
                'subject_mapping': f'User-specified {args.subject}: channels {args.channels}',
                'ttl_mapping': f'User-selected digital input {args.ttl_channel}; hardware mapping must be verified independently of fit residual.',
                'highpass_hz': args.highpass_hz,
                'other_animals': 'Not pooled; one declared acquisition channel group per project.',
                'manual_sorting': 'Reference only, not ground truth'}
            assert not state.events and not state.sorted_spikes
            if args.behavior:
                log(f'IMPORT separate MED-PC behavior; TTL channel {args.ttl_channel}, event code 11')
                sync = import_medpc_behavior(state, args.behavior, ttl_channel=args.ttl_channel)
                log(f"SYNC matched {sync['matched_count']}; mean residual {sync['mean_abs_residual_ms']:.3f} ms; drift {sync['drift_ppm']:.3f} ppm")
            else:
                log('NO BEHAVIOR: electrophysiology-only group; no animal identity inferred and no event analysis')
            save_project(state)
        run_raw_qc(state)
        save_project(state)
        if not state.sorted_spikes:
            log(f'SORT full {state.duration_seconds:.3f} seconds, no animal pooling')
            settings = json.loads(args.sorter_settings.read_text(encoding='utf-8')) if args.sorter_settings else None
            attempt = Path(args.attempt).name if args.attempt else ''
            run_sorter(state, args.sorter, args.output / 'results' / (args.sorter + ('_' + attempt if attempt else '')), log, settings=settings)
            save_project(state)
        compute_unit_metrics(state)
        save_project(state)
        export_reproducible_bundle(state, args.output / 'exports/initial_qc')
        (args.output / 'analysis_constraints.json').write_text(json.dumps(
            state.metadata['delivery_constraints'], indent=2, ensure_ascii=False), encoding='utf-8')
        log(f'SORT AND QC COMPUTED: {len(state.sorted_spikes)} candidate units; event analysis and review remain')
    except Exception:
        log(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
