"""Refresh physical artwork copies from existing exports without rerunning analysis."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from neuroflow.publication_layout import write_sized_figures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--delivery', type=Path, required=True)
    args = parser.parse_args()
    count = 0
    for index in sorted(args.delivery.glob('**/publication/index.html')):
        output = index.parent.parent
        figures = sorted((output / 'figures').glob('*.svg'))
        if not figures:
            continue
        write_sized_figures(output, [p.stem for p in figures])
        text = index.read_text(encoding='utf-8')
        if 'sized_figures/README.md' not in text:
            text = text.replace('</html>', '<p><a href="sized_figures/README.md">Physical-size artwork and checks</a> · <a href="sized_figures/layout_checks.json">Layout diagnostics</a></p></html>')
            index.write_text(text, encoding='utf-8')
        count += 1
    print(f'Prepared physical-size artwork for {count} reports', flush=True)


if __name__ == '__main__':
    main()
