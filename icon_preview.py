"""One background renderer; Tk image creation and callbacks stay on the UI thread."""
from collections import OrderedDict
from io import BytesIO
from pathlib import Path
import queue
import threading
from native_icon import render_icon_png


def file_preview(path, size):
    if not path.is_file():
        raise ValueError(f"找不到图标文件：{path.name}")
    try:
        from PIL import Image
    except ImportError:
        return None
    with Image.open(path, formats=("ICO",)) as image:
        frame = image.ico.getimage((size, size)) if (size, size) in image.ico.sizes() else image
        preview = frame.convert("RGBA")
        preview.thumbnail((size, size), Image.Resampling.LANCZOS)
        output = BytesIO()
        preview.save(output, format="PNG")
        return output.getvalue()


class IconPreviewService:
    def __init__(self, root):
        self.root = root
        self.condition = threading.Condition()
        self.pending = OrderedDict()
        self.versions = {}
        self.results = queue.Queue()
        self.counter = 0
        self.closed = False
        self.thread = threading.Thread(target=self._worker, daemon=True, name='icon-preview')
        self.thread.start()
        self.poll_job = root.after(40, self._poll)

    def request(self, key, source, size, callback, *, priority=False):
        with self.condition:
            if self.closed:
                return
            self.counter += 1
            self.versions[key] = self.counter
            self.pending[key] = (self.counter, source, size, callback)
            if priority:
                self.pending.move_to_end(key, last=False)
            self.condition.notify()

    def cancel(self, prefix):
        with self.condition:
            for key in list(self.versions):
                if key.startswith(prefix):
                    self.versions.pop(key, None)
                    self.pending.pop(key, None)

    def _worker(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.closed or self.pending)
                if self.closed:
                    return
                key, (version, source, size, callback) = self.pending.popitem(last=False)
            try:
                png = file_preview(source, size) if isinstance(source, Path) else render_icon_png(source, size)
                error = None
            except Exception as exc:
                png, error = None, str(exc)
            self.results.put((key, version, callback, png, error))

    def _poll(self):
        if self.closed:
            return
        try:
            for _ in range(24):
                key, version, callback, png, error = self.results.get_nowait()
                if self.versions.get(key) == version:
                    self.versions.pop(key, None)
                    callback(png, error)
        except queue.Empty:
            pass
        finally:
            if not self.closed:
                self.poll_job = self.root.after(40, self._poll)

    def close(self):
        with self.condition:
            self.closed = True
            self.pending.clear()
            self.versions.clear()
            self.condition.notify()
        self.root.after_cancel(self.poll_job)
