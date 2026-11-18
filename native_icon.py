"""Transparent, full-color, multi-size ICO using Windows APIs and the stdlib.

DirectWrite shapes text (including emoji sequences); Direct2D retains font colors.
"""
from __future__ import annotations

from color_renderer import render_color_text
from pathlib import Path
import struct
import zlib
from functools import lru_cache


def png_bytes(width, height, rgba):
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data) & 0xffffffff)
    raw = b''.join(b'\0' + rgba[y*width*4:(y+1)*width*4] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


@lru_cache(maxsize=128)
def render_icon_images(text: str, sizes: tuple[int, ...]) -> tuple[tuple[int, bytes], ...]:
    text = text.strip()
    if not text or len(text) > 32 or any(ord(ch) < 32 for ch in text):
        raise ValueError('图标文本须为 1～32 个可见字符，不能包含换行或控制字符。')
    data, source_size, (left, top, right, bottom) = render_color_text(text)
    images = []
    for size in sizes:
        if not 1 <= size <= 256:
            raise ValueError("图标尺寸须在 1～256 像素之间。")
        width, height = right-left, bottom-top
        factor = (size * .94) / max(width, height)
        dw, dh = max(1, round(width*factor)), max(1, round(height*factor))
        ox, oy = (size-dw)//2, (size-dh)//2
        rgba = bytearray(size*size*4)
        # Average premultiplied color and alpha, then unpremultiply for PNG.
        # This preserves color and prevents dark halos at transparent edges.
        for y in range(dh):
            for x in range(dw):
                blue = green = red = alpha = 0
                for sy in (.125, .375, .625, .875):
                    for sx in (.125, .375, .625, .875):
                        px = min(right-1, left+int((x+sx)*width/dw))
                        py = min(bottom-1, top+int((y+sy)*height/dh))
                        offset = (py*source_size+px)*4
                        blue += data[offset]
                        green += data[offset+1]
                        red += data[offset+2]
                        alpha += data[offset+3]
                p = ((y+oy)*size+x+ox)*4
                if alpha:
                    rgba[p:p+4] = bytes((min(255, round(red*255/alpha)),
                                        min(255, round(green*255/alpha)),
                                        min(255, round(blue*255/alpha)), round(alpha/16)))
        images.append((size, png_bytes(size, size, rgba)))
    return tuple(images)


def render_icon_png(text: str, size: int = 48) -> bytes:
    """Identical pixels to the corresponding ICO frame, with no filesystem writes."""
    return render_icon_images(text, (size,))[0][1]


def render_text_icon(text: str, output_path: Path) -> None:
    images = render_icon_images(text, (16, 24, 32, 48, 64, 128, 256))
    offset = 6 + 16*len(images)
    directory = bytearray(struct.pack('<HHH', 0, 1, len(images)))
    for size, png in images:
        directory.extend(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(png), offset))
        offset += len(png)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(directory + b''.join(png for _, png in images))
