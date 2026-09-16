"""Local-only evidence index: link completed artifacts, explicitly preserve gaps."""
import argparse
import html
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--delivery', type=Path, required=True)
    args = parser.parse_args()
    root = args.delivery.resolve()
    sections = []
    for label, relative in [('四极电极模拟：20分钟', 'tetrode'),
                            ('双探针模拟：修正几何后的20分钟', 'geometry_corrected/neuropixels'),
                            ('真实实验：已确认动物101', 'real/subject101')]:
        cards = []
        for sorter in ('kilosort4', 'mountainsort5', 'spykingcircus2'):
            folder = root / relative / sorter
            reports = sorted(folder.glob('exports/*/publication/index.html'))
            screening = sorted(folder.glob('screened_review/exports/*/publication/index.html'))
            links = []
            for path in reports + screening:
                title = ('自动筛选后 / ' if 'screened_review' in path.parts else '全部候选 / ') + path.parent.parent.name
                links.append(f'<li><a href="{html.escape(path.relative_to(root).as_posix())}">{html.escape(title)}</a></li>')
            for path in folder.glob('**/event_family_review/index.html'):
                title = ('自动筛选后 / ' if 'screened_review' in path.parts else '全部候选 / ') + '跨事件统计复核'
                links.append(f'<li><a href="{html.escape(path.relative_to(root).as_posix())}">{title}</a></li>')
            manifest = folder / 'neuroflow_project.json'
            entry = html.escape(str(manifest)) if manifest.exists() else '项目尚未生成'
            cards.append(f'<article><h3>{sorter}</h3><p class="path">App导入入口：{entry}</p><ul>{"".join(links)}</ul>'
                         + ('<p>有报告不代表质量验收通过，请阅读质量说明。</p>' if reports else '<p>尚无下游报告，不能按完成计。</p>') + '</article>')
        comparison = root / relative / 'sorter_comparison/exports/three_sorter_comparison.png'
        preview = f'<a href="{comparison.relative_to(root).as_posix()}">查看三工具对比图</a>' if comparison.exists() else '三工具对比尚未齐全'
        sections.append(f'<section><h2>{label}</h2><p>{preview}</p><div class="cards">{"".join(cards)}</div></section>')
    page = '<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NeuroEphys AI 实验交付索引</title><style>body{font:15px Arial,"Microsoft YaHei",sans-serif;background:#faf9fb;color:#28232d;max-width:1250px;margin:auto;padding:32px}h1,h2{font-weight:600}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px}article{border:1px solid #ddd4e3;padding:20px;border-radius:8px;background:white}a{color:#705680}li{margin:9px 0}.path{overflow-wrap:anywhere;color:#666;font-size:12px}section{margin-top:36px}.notice{border-left:4px solid #b7a0c7;padding:12px 20px;background:#f0eaf4}</style>'
    page += '<h1>NeuroEphys AI · 实验结果导航</h1><p class="notice">这是工作中交付索引，不是全部完成证明。每种工具独立保存；候选簇、自动筛选和人工验收不是一回事。其余真实动物的身份映射仍待核实，不能跨动物合并。旧的重叠探针几何结果仅保留作失败诊断。</p>'
    page += '<p>先读 <a href="9月16日进度与质量说明.md">进度与质量说明</a>。下方报告包含英文图件、图注草稿和中文解释。App中使用“导入项目”，选择列出的 neuroflow_project.json。</p>'
    page += ''.join(sections) + '<p>最终期刊排版、逐图验收及全部动物分析仍未全部完成。原始数据不修改，私有结果不上传公开GitHub。</p></html>'
    target = root / '实验结果导航.html'
    target.write_text(page, encoding='utf-8')
    print(target)


if __name__ == '__main__':
    main()
