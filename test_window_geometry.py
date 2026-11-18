"""Windows GUI regression: persisted size must survive separate processes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
CHILD = r'''
import json
from pathlib import Path
import sys
sys.path.insert(0, sys.argv[1])
import ctypes
from ctypes import wintypes
from unittest.mock import Mock, patch
import packager_gui as gui
gui.APP_DIR = Path(sys.argv[2])
gui.tkwebui.enable_dpi_awareness()
app = gui.PackagerApp()
errors = []
app.report_callback_exception = lambda *args: errors.append(str(args))
action = sys.argv[3]
user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t

def finish():
    hwnd = user32.GetAncestor(app.winfo_id(), 2)
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    y = app.titlebar.winfo_rooty() + app.titlebar.winfo_height() // 2
    points = [rect.left + (rect.right - rect.left) * part // 4 for part in (1, 2)]
    hits = [user32.SendMessageW(hwnd, 0x84, 0, ((y & 65535) << 16) | (x & 65535)) for x in points]
    print(json.dumps({'client': [app.winfo_width(), app.winfo_height()], 'hits': hits,
                      'min_height': app.minsize()[1], 'form_scroll': bool(app.project_scroll.bar.winfo_ismapped()),
                      'state': app.state(), 'errors': errors}), flush=True)
    app._on_close()

def act():
    if action == 'resize':
        app.geometry(f"1080x{max(760, app.minsize()[1] + 40)}")
        app.after(150, finish)
    elif action == 'disclosure-after-move':
        chrome = app.chrome
        area = chrome.work_area().rcWork
        chrome.u.SetWindowPos(chrome.hwnd, None, area.left + 82, area.top + 112, 0, 0, 0x0001 | 0x0004 | 0x0010)
        app.after(150, open_disclosure)
    elif action == 'cancel-close':
        app.worker_thread = Mock()
        with patch.object(gui.messagebox, 'askyesno', return_value=False) as confirm:
            app.chrome.buttons['close'].invoke()
            app.update()
            confirm.assert_called_once()
        app.worker_thread = None
        assert app.chrome.attached
        app.chrome.buttons['pin'].invoke()
        assert app.tk.getboolean(app.attributes('-topmost'))
        app.chrome.buttons['pin'].invoke()
        assert not app.tk.getboolean(app.attributes('-topmost'))
        app.after(150, finish)
    elif action == 'maximize-restore':
        app.state('zoomed')
        app.after(150, restore)
    else:
        finish()
def window_position():
    chrome = app.chrome
    rect = chrome.w.RECT()
    chrome.u.GetWindowRect(chrome.hwnd, chrome.c.byref(rect))
    return rect.left, rect.top

def open_disclosure():
    position = window_position()
    app.advanced_options.header.invoke()
    app.after(200, lambda: fold_disclosure(position))

def fold_disclosure(position):
    if window_position() != position:
        errors.append(f"Window moved on expand: {position} to {window_position()}")
    app.advanced_options.header.invoke()
    def check():
        if window_position() != position:
            errors.append(f"Window moved on collapse: {position} to {window_position()}")
        finish()
    app.after(200, check)

def restore():
    app.state('normal')
    app.after(150, finish)
app.after(350, act)
app.mainloop()
'''


@unittest.skipUnless(os.name == 'nt', 'Windows caption and geometry regression')
class WindowGeometryTests(unittest.TestCase):
    def test_restart_resize_and_maximize_restore(self):
        with tempfile.TemporaryDirectory(prefix='packager-window-') as folder:
            config = Path(folder)/'settings.json'
            config.write_text(json.dumps({'settings_version':11, 'window_size':'1000x700', 'last_project':''}))
            expected_width, saved_height = 1000, 700
            for action in ['reopen']*5 + ['resize', 'reopen', 'maximize-restore', 'cancel-close', 'disclosure-after-move', 'reopen']:
                result = subprocess.run([sys.executable, '-B', '-c', CHILD, str(ROOT), folder, action],
                    cwd=folder, capture_output=True, text=True, encoding='utf-8', timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                self.assertFalse(data['errors'])
                self.assertFalse(data['form_scroll'])
                self.assertEqual(data['hits'], [2, 2])  # HTCAPTION
                if action == 'resize':
                    expected_width, saved_height = 1080, max(760, data['min_height'] + 40)
                saved_height = max(saved_height, data['min_height'])
                expected = [expected_width, saved_height]
                self.assertEqual(data['client'], expected)
                self.assertEqual(json.loads(config.read_text())['window_size'], f'{expected[0]}x{expected[1]}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
