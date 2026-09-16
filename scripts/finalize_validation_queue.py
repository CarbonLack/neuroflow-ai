"""Follow a finite compute queue and produce auditable postprocessing artifacts.

Completion means artifact generation only; manual/scientific acceptance stays open.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--max-hours', type=float, default=12)
    args = parser.parse_args()
    config = json.loads(args.manifest.read_text(encoding='utf-8'))
    queue_path = args.manifest.with_name(args.manifest.stem + '_status.json')
    output = args.manifest.with_name('postprocessing_status.json')
    results = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
    repo = Path(__file__).resolve().parents[1]
    deadline = time.monotonic() + args.max_hours * 3600
    def run(script, arguments, key):
        with output.with_name('postprocessing_console.log').open('a', encoding='utf-8') as log:
            log.write(f'\n{key}\n')
            log.flush()
            return subprocess.run([sys.executable, str(repo / 'scripts' / script), *arguments],
                                  cwd=repo, stdout=log, stderr=subprocess.STDOUT).returncode
    while time.monotonic() < deadline:
        try:
            status = json.loads(queue_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            time.sleep(15)
            continue
        for job in config['jobs']:
            key = job['name']
            if status.get(key, {}).get('status') != 'complete' or key in results:
                continue
            project = Path(job['output'])
            if '--no-behavior' in job['arguments']:
                results[key] = {'status': 'electrophysiology_only', 'manual_review': 'pending'}
            else:
                code = run('analyze_saved_medpc_project.py', ['--project', str(project), '--qc-screen'], key)
                screened = project / 'screened_review'
                if code == 0 and (screened / 'exports/event_analysis_summary.json').exists():
                    code = run('review_event_family.py', ['--project', str(screened)], key + '_family')
                results[key] = {'status': 'generated' if code == 0 else 'failed',
                                'exit_code': code, 'manual_review': 'pending'}
            output.write_text(json.dumps(results, indent=2), encoding='utf-8')
        for batch in sorted({str(Path(j['output']).parent) for j in config['jobs']}):
            group = [j for j in config['jobs'] if str(Path(j['output']).parent) == batch]
            key = 'comparison:' + batch
            if key not in results and all(status.get(j['name'], {}).get('status') == 'complete' for j in group):
                code = run('combine_delivery_sorters.py', ['--batch', batch], key)
                results[key] = {'status': 'generated' if code == 0 else 'failed', 'exit_code': code,
                                'manual_review': 'pending'}
                output.write_text(json.dumps(results, indent=2), encoding='utf-8')
        if all(status.get(j['name'], {}).get('status') in ('complete', 'failed') for j in config['jobs']):
            run('summarize_real_validation.py', ['--delivery', str(args.manifest.parent)], 'summary')
            run('prepare_publication_layouts.py', ['--delivery', str(args.manifest.parent)], 'publication_layouts')
            run('audit_exported_figures.py', ['--delivery', str(args.manifest.parent)], 'figure_audit')
            run('build_delivery_index.py', ['--delivery', str(args.manifest.parent)], 'navigation')
            break
        time.sleep(30)
    else:
        results['queue_timeout'] = {'status': 'incomplete', 'reason': 'Finite postprocessing wait expired; inspect queue, do not assume completion'}
        output.write_text(json.dumps(results, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
