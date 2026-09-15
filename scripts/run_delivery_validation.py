"""Run actual full-length import/sorting/analysis through application APIs."""
import argparse
import csv
import json
import sys
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from neuroflow.data_import import import_binary_recording
from neuroflow.project import save_project, load_project
from neuroflow.synchronization import import_behavior_events
from neuroflow.analysis import run_raw_qc, preprocessing_preview, compute_unit_metrics, event_aligned_analysis, export_reproducible_bundle
from neuroflow.sorting import run_sorter
from neuroflow.figures import raw_overview_figure, qc_diagnostics_figure, synchronization_figure, unit_metrics_figure, event_analysis_figure, behavior_figure
from neuroflow.figures import statistics_figure, neural_toolkit_figure
from neuroflow.statistics import run_statistical_suite
from neuroflow.ephys_toolkit import run_spike_train_suite


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--electrode', required=True, choices=['tetrode', 'neuropixels'])
    parser.add_argument('--sorter', required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    def log(message):
        line = f'{datetime.now().isoformat(timespec="seconds")} {message}'
        print(line, flush=True)
        with (args.output / 'execution.log').open('a', encoding='utf-8') as f:
            f.write(line + '\n')
    manifest = args.output / 'neuroflow_project.json'
    try:
        if manifest.exists():
            state = load_project(manifest)
        else:
            meta = json.loads((args.source / 'raw/metadata.json').read_text(encoding='utf-8'))
            log('IMPORT raw voltage; no preloaded project or sorting')
            state = import_binary_recording(args.output, args.source / 'raw/recording.bin', 30000,
                32 if args.electrode == 'tetrode' else 128, scale_uv_per_bit=0.195, electrode_type=args.electrode)
            assert not state.events and not state.sorted_spikes
            with (args.source / 'raw/channel_geometry.csv').open(encoding='utf-8-sig') as f:
                geometry = list(csv.DictReader(f))
            state.metadata['contact_positions_um'] = [[float(r['x_position_um']),float(r['y_position_um'])] for r in geometry]
            state.metadata['source_metadata'] = meta
            log('IMPORT behavior events from CSV, shared simulation clock')
            import_behavior_events(state, args.source / 'raw/events.csv')
            state.metadata['language'] = 'en_US'
            state.name = f'{args.electrode} full 20min - {args.sorter}'
            save_project(state)
        figures = args.output / 'exports/figures'
        figures.mkdir(parents=True, exist_ok=True)
        def render(name, function):
            fig = function(state)
            fig.canvas.draw()
            fig.savefig(figures / f'{name}.png', dpi=180, bbox_inches='tight')
            fig.savefig(figures / f'{name}.svg', bbox_inches='tight')
            plt.close(fig)
            log(f'RENDERED {name}; visual review pending')
        log('QC and preprocessing diagnostics')
        run_raw_qc(state)
        preprocessing_preview(state)
        for name, fn in [('raw',raw_overview_figure),('raw_qc',qc_diagnostics_figure),('synchronization',synchronization_figure),('behavior',behavior_figure)]:
            render(name, fn)
        save_project(state)
        log(f'SORT full duration {state.duration_seconds} s using {args.sorter}')
        if not state.sorted_spikes:
            run_sorter(state,args.sorter,args.output / 'results' / args.sorter,log)
            save_project(state)
        log(f'SORT COMPLETE: {len(state.sorted_spikes)} units')
        compute_unit_metrics(state)
        render('unit_qc',unit_metrics_figure)
        original_events = state.events
        for event_type in sorted({e['event_type'] for e in original_events}):
            state.events = [e for e in original_events if e['event_type']==event_type]
            event_aligned_analysis(state)
            render(f'event_{event_type}',event_analysis_figure)
            run_statistical_suite(state)
            render(f'statistics_{event_type}', statistics_figure)
            run_spike_train_suite(state)
            render(f'spike_statistics_{event_type}', lambda s: neural_toolkit_figure(s, 'spike:statistics'))
            export_reproducible_bundle(state,args.output / 'exports' / event_type)
        state.events = original_events
        save_project(state)
        log('COMPUTATION COMPLETE; downstream extensions and image review remain')
    except Exception:
        log(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
