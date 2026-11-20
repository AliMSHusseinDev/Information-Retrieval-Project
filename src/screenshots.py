"""Persist PNG screenshots rendered by the browser."""
import os
import re
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4
from zlib import crc32


def save_screenshot(folder, page, label, payload):
    # Verify the PNG container, including chunk bounds and checksums, before saving.
    if not payload.startswith(b'\x89PNG\r\n\x1a\n') or payload[8:16] != b'\x00\x00\x00\rIHDR':
        raise ValueError('Invalid PNG header.')
    offset = 8
    pixels = False
    while offset + 12 <= len(payload):
        size = int.from_bytes(payload[offset:offset + 4], 'big')
        kind = payload[offset + 4:offset + 8]
        end = offset + 8 + size
        checksum = int.from_bytes(payload[end:end + 4], 'big')
        if end + 4 > len(payload) or crc32(memoryview(payload)[offset + 4:end]) != checksum:
            raise ValueError('Invalid PNG chunk.')
        offset = end + 4
        if kind == b'IDAT' and size:
            pixels = True
        if kind == b'IEND':
            if not pixels or size or offset != len(payload):
                raise ValueError('Invalid PNG ending.')
            break
    else:
        raise ValueError('Incomplete PNG image.')
    label = re.sub(r'[^\w-]+', '-', label[:60]).strip('-')
    name = '-'.join(filter(None, (page, label, datetime.now().strftime('%Y%m%d-%H%M%S'),
                                  uuid4().hex[:10]))) + '.png'
    temp = NamedTemporaryFile(dir=folder, delete=False)
    path = Path(temp.name)
    try:
        with temp:
            temp.write(payload)
        os.replace(path, folder / name)
    finally:
        path.unlink(missing_ok=True)
    return name
