"""Save a static, self-contained browser SVG of the selected results."""

import os
import re
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4
from xml.etree import ElementTree as ET


HTML = 'http://www.w3.org/1999/xhtml'
SVG = 'http://www.w3.org/2000/svg'
TAGS = set('div span p h1 h2 h3 h4 section article aside strong b small i br mark header '
           'details summary table thead tbody tr td th pre code ul ol li'.split())
STYLE = re.compile(r'(?:width:\s*[\d.]+%|(?:background-color|color):\s*(?:#[\da-fA-F]{3,8}|rgba?\([\d., %]+\)))')


def save_screenshot(folder, static_dir, page, data):
    if not isinstance(data, dict):
        raise ValueError('Invalid screenshot data.')
    width, height = data.get('width'), data.get('height')
    if any(type(size) is not int or not 0 < size <= 10000000 for size in (width, height)):
        raise ValueError('Invalid screenshot dimensions.')
    markup = data.get('content')
    if not isinstance(markup, str) or '<!' in markup or '<?' in markup:
        raise ValueError('Invalid screenshot content.')
    try:
        content = ET.fromstring(markup)
    except ET.ParseError as error:
        raise ValueError('Invalid screenshot markup.') from error
    if content.tag != f'{{{HTML}}}div':
        raise ValueError('Invalid screenshot root.')
    for node in content.iter():
        if node.tag.startswith('{' + SVG + '}'):
            if node.tag.split('}')[1] not in ('svg', 'text', 'rect', 'line', 'title'):
                raise ValueError('Unsupported chart element.')
            for name, value in list(node.attrib.items()):
                if name in ('x', 'y', 'x1', 'x2', 'y1', 'y2', 'width', 'height', 'rx', 'font-size', 'viewBox') and re.fullmatch(r'[-+0-9.eE ]+', value):
                    continue
                if name in ('fill', 'stroke') and re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                    continue
                if name == 'transform' and re.fullmatch(r'translate\([-+0-9.eE ]+\) rotate\([-+0-9.eE]+\)', value):
                    continue
                if name == 'text-anchor' and value in ('start', 'middle', 'end'):
                    continue
                if name == 'dominant-baseline' and value == 'central':
                    continue
                del node.attrib[name]
            continue
        tag = node.tag.removeprefix(f'{{{HTML}}}')
        if node.tag != f'{{{HTML}}}{tag}' or tag not in TAGS:
            raise ValueError('Unsupported screenshot element.')
        for name, value in list(node.attrib.items()):
            if name in ('class', 'id', 'open'):
                continue
            if name == 'style' and all(STYLE.fullmatch(s.strip()) for s in value.split(';') if s.strip()):
                continue
            del node.attrib[name]
    # ElementTree keeps the XHTML prefix on the embedded layout.
    svg = ET.Element('svg', xmlns='http://www.w3.org/2000/svg', width=str(width),
                     height=str(height), viewBox=f'0 0 {width} {height}')
    css_dir = Path(static_dir) / 'css'
    ET.SubElement(svg, 'style').text = ((css_dir / 'style.css').read_text(encoding='utf-8')
                                        + (css_dir / 'capture.css').read_text(encoding='utf-8'))
    frame = ET.SubElement(svg, 'foreignObject', width='100%', height='100%')
    frame.append(content)
    label = re.sub(r'[^\w-]+', '-', str(data.get('label', ''))[:60]).strip('-')
    name = '-'.join(filter(None, (page, label, datetime.now().strftime('%Y%m%d-%H%M%S'),
                                  uuid4().hex[:10]))) + '.svg'
    payload = ET.tostring(svg, encoding='utf-8')
    temp = NamedTemporaryFile(dir=folder, delete=False)
    path = Path(temp.name)
    try:
        with temp:
            temp.write(payload)
        os.replace(path, folder / name)
    finally:
        path.unlink(missing_ok=True)
    return name
