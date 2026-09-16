"""Mechanical export checks; explicitly not a scientific or visual sign-off."""
import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--delivery', type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for svg in sorted(args.delivery.glob('**/exports/**/figures/*.svg')):
        row = {'file': str(svg), 'checks': [], 'manual_review': 'not certified by this audit'}
        try:
            root = ET.parse(svg).getroot()
            text = [''.join(n.itertext()) for n in root.iter() if n.tag.endswith('}text')]
            cjk = [t for t in text if re.search(r'[\u3400-\u9fff]', t)]
            box = [float(x) for x in root.attrib.get('viewBox', '').split()]
            if len(box) != 4 or box[2] <= 0 or box[3] <= 0:
                row['checks'].append('invalid_viewbox')
            if cjk:
                row['checks'].append('non_english_text')
                row['cjk_text'] = cjk
            png = svg.with_suffix('.png')
            if not png.exists() or png.stat().st_size < 100:
                row['checks'].append('missing_or_empty_png')
            row['status'] = 'needs_review' if row['checks'] else 'mechanical_checks_passed'
        except Exception as exc:
            row['status'] = 'unreadable'
            row['error'] = str(exc)
        rows.append(row)
    report = {'scope': 'SVG readability, physical coordinate box, English text and paired PNG existence only; not validation of statistics, rendering or interpretation',
              'figure_count': len(rows), 'flagged_count': sum(r['status'] != 'mechanical_checks_passed' for r in rows), 'figures': rows}
    target = args.delivery / 'figure_integrity_audit.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"{report['figure_count']} figures checked; {report['flagged_count']} flagged; {target}", flush=True)


if __name__ == '__main__':
    main()
