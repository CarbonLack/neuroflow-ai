import xml.etree.ElementTree as ET
from neuroflow.publication_layout import write_sized_figures


def test_physical_resize_preserves_viewbox_and_source(tmp_path):
    folder = tmp_path / 'figures'
    folder.mkdir()
    original = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 400"><text style="font-size: 8px">Time</text></svg>'
    (folder / 'test.svg').write_text(original)
    result = write_sized_figures(tmp_path, ['test'])
    assert result['figures'][0]['width_mm'] == 183
    assert result['figures'][0]['height_mm'] <= 170
    assert (folder / 'test.svg').read_text() == original
    svg = ET.parse(tmp_path / 'publication/sized_figures/test.svg').getroot()
    assert svg.attrib['viewBox'] == '0 0 700 400'
    assert list(svg)[0].text == 'Time'
