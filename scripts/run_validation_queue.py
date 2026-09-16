"""Serial, resumable validation queue; private dataset paths live in a local manifest."""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.manifest.read_text(encoding='utf-8'))
    repo = Path(__file__).resolve().parents[1]
    status_path = args.manifest.with_name(args.manifest.stem + '_status.json')
    status = json.loads(status_path.read_text(encoding='utf-8')) if status_path.exists() else {}
    def persist():
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
    for job in config['jobs']:
        name = job['name']
        if status.get(name, {}).get('status') == 'complete':
            continue
        output = Path(job['output'])
        output.mkdir(parents=True, exist_ok=True)
        status[name] = {'status': 'running', 'started': datetime.now().isoformat(), 'output': str(output)}
        persist()
        steps = [('sorting_qc', 'run_real_delivery.py', job['arguments'] + ['--output', str(output)])]
        if '--no-behavior' not in job['arguments']:
            steps += [('events', 'analyze_saved_medpc_project.py', ['--project', str(output)]),
                      ('event_family', 'review_event_family.py', ['--project', str(output)])]
        for label, script, arguments in steps:
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log = output / f'queue_{label}_{stamp}.log'
            print(f'{name}: {label}', flush=True)
            with log.open('w', encoding='utf-8') as stream:
                result = subprocess.run([sys.executable, '-u', str(repo / 'scripts' / script), *arguments],
                                        cwd=repo, stdout=stream, stderr=subprocess.STDOUT)
            status[name][label] = {'exit_code': result.returncode, 'log': str(log)}
            persist()
            if result.returncode:
                status[name]['status'] = 'failed'
                break
        else:
            status[name]['status'] = 'complete'
        status[name]['finished'] = datetime.now().isoformat()
        persist()
    print(status_path, flush=True)


if __name__ == '__main__':
    main()
