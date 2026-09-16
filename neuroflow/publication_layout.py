"""Physical-size SVG export with explicit checks, not a journal-acceptance claim."""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET

SOURCE = 'https://www.nature.com/nature/for-authors/final-submission'


def write_sized_figures(output: Path, names: list[str]) -> dict:
    target = output / 'publication' / 'sized_figures'
    target.mkdir(parents=True, exist_ok=True)
    records = []
    for name in names:
        source = output / 'figures' / f'{name}.svg'
        if not source.exists():
            continue
        tree = ET.parse(source)
        svg = tree.getroot()
        box = [float(x) for x in svg.attrib['viewBox'].split()]
        width, height = box[2:]
        if width <= 0 or height <= 0:
            raise ValueError('SVG viewBox must have positive dimensions')
        width_mm = min(183.0, 170.0 * width / height)
        height_mm = width_mm * height / width
        scale_to_pt = width_mm * 72 / 25.4 / width
        sizes = []
        for node in svg.iter():
            if node.tag.endswith('}text'):
                style = node.attrib.get('style', '')
                match = re.search(r'font-size:\s*([\d.]+)px', style)
                if match:
                    sizes.append(float(match.group(1)) * scale_to_pt)
        svg.set('width', f'{width_mm:.4f}mm')
        svg.set('height', f'{height_mm:.4f}mm')
        destination = target / source.name
        tree.write(destination, encoding='utf-8', xml_declaration=True)
        records.append({'figure': name, 'width_mm': width_mm, 'height_mm': height_mm,
                        'minimum_detected_text_pt': min(sizes) if sizes else None,
                        'maximum_detected_text_pt': max(sizes) if sizes else None,
                        'text_size_review_required': not sizes or min(sizes) < 5 or max(sizes) > 7,
                        'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()})
    result = {'profile': 'Nature double-column starting profile', 'source': SOURCE,
              'scope': 'Resizes SVG physical dimensions without altering plotted data, axes or viewBox. Font bounds are diagnostics, not full artwork certification.',
              'manual_checks': ['Inspect all text at final size', 'Check raster components and font availability',
                                'Export a journal-accepted final format', 'Review scientific selection and captions',
                                'Cell and Science require their own specifications'], 'figures': records}
    (target / 'layout_checks.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    (target / 'README.md').write_text(
        '# 物理尺寸图件与检查\n\n按Nature双栏起点：宽不超过183mm、高不超过170mm。'
        '只改SVG物理尺寸，保留数据、坐标和矢量内容；源图不覆盖。\n\n'
        'layout_checks.json记录最终尺寸和能识别的文字大小；超出5–7pt的普通文字范围会提示复核。'
        '面板标记等特殊文字仍需人工检查；这不是投稿合格证。SVG是可编辑中间稿，需另导出期刊接受的最终格式。'
        'Cell、Science并不存在与Nature完全一致的通用标准，投稿前应选择目标期刊核对。\n\n来源：' + SOURCE,
        encoding='utf-8')
    return result
