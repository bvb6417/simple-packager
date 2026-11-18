"""Headless DirectWrite + Direct2D color text renderer (Windows stdlib only).

Uses a software WIC render target and D2D1_DRAW_TEXT_OPTIONS_ENABLE_COLOR_FONT.
https://learn.microsoft.com/windows/win32/directwrite/color-fonts
"""
import ctypes as c
import os
import uuid


class GUID(c.Structure):
    _fields_ = [('data1', c.c_uint32), ('data2', c.c_uint16),
                ('data3', c.c_uint16), ('data4', c.c_ubyte * 8)]
    @classmethod
    def parse(cls, text):
        return cls.from_buffer_copy(uuid.UUID(text).bytes_le)


class PixelFormat(c.Structure):
    _fields_ = [('format', c.c_uint32), ('alpha', c.c_uint32)]


class TargetProperties(c.Structure):
    _fields_ = [('type', c.c_uint32), ('pixel', PixelFormat), ('dpi_x', c.c_float),
                ('dpi_y', c.c_float), ('usage', c.c_uint32), ('feature_level', c.c_uint32)]


class Color(c.Structure):
    _fields_ = [(name, c.c_float) for name in ('r', 'g', 'b', 'a')]


class Point(c.Structure):
    _fields_ = [('x', c.c_float), ('y', c.c_float)]


class Metrics(c.Structure):
    _fields_ = [(name, c.c_float) for name in
                ('left', 'top', 'width', 'trailing_width', 'height', 'layout_width', 'layout_height')]
    _fields_ += [('max_bidi_depth', c.c_uint32), ('line_count', c.c_uint32)]


def _method(obj, slot, result, *args):
    table = c.cast(obj, c.POINTER(c.POINTER(c.c_void_p))).contents
    return c.WINFUNCTYPE(result, c.c_void_p, *args)(table[slot])


def _check(hr):
    if hr < 0:
        raise OSError(f'Windows 彩色字体渲染失败：HRESULT 0x{hr & 0xffffffff:08X}')


def render_color_text(text):
    """Return premultiplied BGRA pixels, square width and visible bounding box."""
    if os.name != 'nt':
        raise RuntimeError('文字图标需要 Windows；其他系统请使用现成的 .ico。')
    ptr, uint, real, hr = c.c_void_p, c.c_uint32, c.c_float, c.c_int32
    pp, gp = c.POINTER(ptr), c.POINTER(GUID)
    ole = c.WinDLL('ole32')
    ole.CoInitializeEx.argtypes, ole.CoInitializeEx.restype = [ptr, uint], hr
    ole.CoUninitialize.argtypes, ole.CoUninitialize.restype = [], None
    ole.CoCreateInstance.argtypes, ole.CoCreateInstance.restype = [gp, ptr, uint, gp, pp], hr
    init = ole.CoInitializeEx(None, 0)
    if init < 0 and init != -2147417850:  # RPC_E_CHANGED_MODE: use existing apartment.
        _check(init)
    objects = []
    def output():
        obj = ptr()
        objects.append(obj)
        return obj
    try:
        wic = output()
        _check(ole.CoCreateInstance(c.byref(GUID.parse('cacaf262-9370-4615-a13b-9f5539da4c0a')),
            None, 1, c.byref(GUID.parse('ec5ec8a9-c395-4314-9c77-54d7a935ff70')), c.byref(wic)))
        size = 768
        bitmap = output()
        pixel_guid = GUID.parse('6fddc324-4e03-4bfe-b185-3d77768dc910')
        _check(_method(wic, 17, hr, uint, uint, gp, uint, pp)(wic, size, size, c.byref(pixel_guid), 2, c.byref(bitmap)))
        d2d = c.WinDLL('d2d1')
        d2d.D2D1CreateFactory.argtypes, d2d.D2D1CreateFactory.restype = [uint, gp, ptr, pp], hr
        factory = output()
        _check(d2d.D2D1CreateFactory(0, c.byref(GUID.parse('06152247-6f50-465a-9245-118bfd3b6007')), None, c.byref(factory)))
        target = output()
        # BGRA8 UNORM, premultiplied alpha, 96 DPI, software renderer.
        properties = TargetProperties(1, PixelFormat(87, 1), 96, 96, 0, 0)
        _check(_method(factory, 13, hr, ptr, c.POINTER(TargetProperties), pp)(factory, bitmap, c.byref(properties), c.byref(target)))
        dwrite = c.WinDLL('dwrite')
        dwrite.DWriteCreateFactory.argtypes, dwrite.DWriteCreateFactory.restype = [uint, gp, pp], hr
        writer = output()
        _check(dwrite.DWriteCreateFactory(0, c.byref(GUID.parse('b859ee5a-d838-4b5b-a2e8-1adc7d93db48')), c.byref(writer)))
        length = len(text.encode('utf-16-le')) // 2
        def layout(font_size, extent):
            fmt, result = output(), output()
            _check(_method(writer, 15, hr, c.c_wchar_p, ptr, uint, uint, uint, real, c.c_wchar_p, pp)(
                writer, 'Segoe UI Emoji', None, 400, 0, 5, font_size, 'zh-cn', c.byref(fmt)))
            _check(_method(fmt, 3, hr, uint)(fmt, 2))  # Center horizontally.
            _check(_method(fmt, 4, hr, uint)(fmt, 2))  # Center vertically.
            _check(_method(fmt, 5, hr, uint)(fmt, 1))  # No wrapping.
            _check(_method(writer, 18, hr, c.c_wchar_p, uint, ptr, real, real, pp)(
                writer, text, length, fmt, extent, extent, c.byref(result)))
            return result
        measure = layout(480, 16384)
        metrics = Metrics()
        _check(_method(measure, 60, hr, c.POINTER(Metrics))(measure, c.byref(metrics)))
        if metrics.width <= 0 or metrics.height <= 0:
            raise ValueError('该文本没有生成可见图形。')
        text_layout = layout(480 * (size - 64) / max(metrics.width, metrics.height), size)
        brush = output()
        foreground = Color(30/255, 41/255, 59/255, 1)
        _check(_method(target, 8, hr, c.POINTER(Color), ptr, pp)(target, c.byref(foreground), None, c.byref(brush)))
        _method(target, 34, None, uint)(target, 2)  # Grayscale antialias on transparent surface.
        _method(target, 48, None)(target)
        transparent = Color(0, 0, 0, 0)
        _method(target, 47, None, c.POINTER(Color))(target, c.byref(transparent))
        _method(target, 28, None, Point, ptr, ptr, uint)(target, Point(0, 0), text_layout, brush, 4)
        _check(_method(target, 49, hr, ptr, ptr)(target, None, None))
        pixels = (c.c_ubyte * (size*size*4))()
        _check(_method(bitmap, 7, hr, ptr, uint, uint, ptr)(bitmap, None, size*4, len(pixels), pixels))
        data = bytes(pixels)
        positions = [i for i in range(size*size) if data[i*4+3]]
        if not positions:
            raise ValueError('该文本没有生成可见图形，请尝试其他字符。')
        bounds = (min(i % size for i in positions), positions[0] // size,
                  max(i % size for i in positions)+1, positions[-1] // size+1)
        return data, size, bounds
    finally:
        for obj in reversed(objects):
            if obj:
                _method(obj, 2, uint)(obj)
        if init >= 0:
            ole.CoUninitialize()
