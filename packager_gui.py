from __future__ import annotations
import tkinter as tk
from tkinter import font as tkfont, filedialog, messagebox, ttk
import ctypes
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading

from packager_core import (
    APP_DIR,
    APP_NAME,
    APP_VERSION,
    DEFAULT_REQUIREMENTS_NAME,
    ENTRY_PRIORITIES,
    FAST_DEPENDENCY_MODE,
    GENERATED_REQUIREMENTS_MARKER,
    LOCKED_DEPENDENCY_MODE,
    PACKAGE_ICON_PNG,
    SKIP_DIRS,
    PackagerController,
    dependency_output_path,
    is_generated_requirements,
    locate_uv,
    project_settings_path,
    scan_local_requirements,
    uv_cache_directory,
)
from system_python_launcher import build_system_python_launcher
import tkwebui
from tkwebui import RoundedText


from packager_layout import LayoutMixin, icon_button, text_scrollbar
from icon_preview import IconPreviewService
from emoji_picker import EmojiPicker


class PackagerApp(LayoutMixin, PackagerController, tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.dialogs = messagebox
        self.busy = False
        self.title(f"{APP_NAME} {APP_VERSION}")
        self._set_window_icon()
        self._set_initial_geometry()
        self.minsize(min(800, self.winfo_screenwidth()-40), min(600, self.winfo_screenheight()-80))

        self.uv_path: Path | None = None
        self.running_process: subprocess.Popen[str] | None = None
        self.worker_thread: threading.Thread | None = None
        self.task_queue: queue.Queue[tuple] = queue.Queue()
        self.cancel_requested = False
        self.task_success_callback = None
        self.active_project_path: Path | None = None
        self.file_drop_bindings: list[tuple[int, int, object]] = []
        self.file_drop_queue: queue.Queue[tuple] = queue.Queue()

        self.config_path = APP_DIR / "settings.json"

        self.project_var = tk.StringVar()
        self.entry_var = tk.StringVar()
        self.output_name_var = tk.StringVar()
        self.icon_input_var = tk.StringVar()
        self.dist_var = tk.StringVar()
        self.python_version_var = tk.StringVar(value="系统默认（最快）")
        self.pyinstaller_version_var = tk.StringVar(
            value="自动"
        )
        self.package_mode_var = tk.StringVar(value="单文件（--onefile）")
        self.window_mode_var = tk.StringVar(value="显示命令行窗口（--console）")
        self.preset_var = tk.StringVar(value="标准（推荐）")
        self.clean_var = tk.BooleanVar(value=True)
        self.delete_cache_after_build_var = tk.BooleanVar(value=True)

        self.requirements_var = tk.StringVar()
        self.dependency_mode_var = tk.StringVar(value=FAST_DEPENDENCY_MODE)

        self.hidden_imports_var = tk.StringVar()
        self.excludes_var = tk.StringVar()
        self.exclude_dev_var = tk.BooleanVar(value=False)
        self.auto_collect_data_var = tk.BooleanVar(value=True)
        self.uv_status_var = tk.StringVar(value="正在检查 uv…")
        self.task_status_var = tk.StringVar(value="就绪")

        self._configure_style()
        self._build_ui()
        self._preview_job = None
        self.preview_service = IconPreviewService(self)
        self.icon_input_var.trace_add('write', self._queue_icon_preview)
        self.package_mode_var.trace_add("write", self._update_dependency_action_state)
        self._load_settings()
        self._update_dependency_action_state()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after_idle(self._fit_form_height)
        self.after(100, self._install_file_drops)
        self.after(50, self._poll_file_drop_queue)
        self.after(100, self._poll_task_queue)
        self.after(250, self.check_uv)


    def _set_window_icon(self) -> None:
        try:
            self.window_icon_image = tk.PhotoImage(data=PACKAGE_ICON_PNG).subsample(2, 2)
            self.iconphoto(True, self.window_icon_image)
        except tk.TclError:
            self.window_icon_image = None


    def _set_initial_geometry(self) -> None:
        screen_width, screen_height = self._available_screen_size()
        width = min(1120, screen_width - 40)
        height = min(900, screen_height - 64)
        self._center_window(width, height)


    def _toggle_advanced_options(self):
        if not self.advanced_options.opened:
            self._collapsed_height = self.winfo_height()
        self.advanced_options.toggle()
        preferred = None if self.advanced_options.opened else self._collapsed_height
        self.after_idle(lambda: self._fit_form_height(preferred, keep_position=True))

    def _fit_form_height(self, preferred_height=None, *, keep_position=False):
        self.update_idletasks()
        height = self.winfo_height()
        viewport = self.project_scroll.canvas.winfo_height()
        # WindowChrome can process idle callbacks before it has attached.
        if viewport <= 1 or (os.name == "nt" and not self.chrome.attached):
            self.after(30, lambda: self._fit_form_height(preferred_height, keep_position=keep_position))
            return
        # Reserve one status row so progress and icon feedback also fit.
        allowance = tkfont.nametofont("TkDefaultFont").metrics("linespace") + self.progress.winfo_reqheight() + 12
        content = self.project_scroll.body.winfo_reqheight()
        left, top, screen_width, screen_height = self._available_screen_bounds()
        width = self.winfo_width()
        frame_width = frame_height = 0
        if os.name == "nt":
            from ctypes import wintypes
            rect = wintypes.RECT()
            hwnd = wintypes.HWND(int(self.wm_frame(), 0))
            if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                frame_width = max(0, rect.right - rect.left - width)
                frame_height = max(0, rect.bottom - rect.top - height)
                if keep_position and self.chrome.attached:
                    area = self.chrome.work_area()
                    if area is not None:
                        screen_height = area.rcWork.bottom - rect.top
        capacity = max(height if keep_position else 1, screen_height - frame_height - 16)
        minimum = min(height - viewport + content + allowance, capacity)
        target = min(max(preferred_height or height, minimum), capacity)
        self.minsize(self.minsize()[0], minimum)
        if target != height and self.state() == "normal":
            size = f"{width}x{target}"
            if keep_position:
                self.geometry(size)
            else:
                x = left + max(0, (screen_width - width - frame_width) // 2)
                y = top + max(0, (screen_height - target - frame_height) // 2)
                self.geometry(f"{size}+{x}+{y}")
            self.after(80, self.chrome.schedule_cache)

    def _available_screen_size(self) -> tuple[int, int]:
        _, _, width, height = self._available_screen_bounds()
        return width, height


    def _available_screen_bounds(self) -> tuple[int, int, int, int]:
        if os.name == "nt":
            class Rect(ctypes.Structure):
                _fields_ = (
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                )

            work_area = Rect()
            if ctypes.windll.user32.SystemParametersInfoW(
                0x0030, 0, ctypes.byref(work_area), 0
            ):
                return (
                    work_area.left,
                    work_area.top,
                    work_area.right - work_area.left,
                    work_area.bottom - work_area.top,
                )
        return 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()


    def _center_window(self, width: int, height: int) -> None:
        left, top, screen_width, screen_height = self._available_screen_bounds()
        x = left + max(0, (screen_width - width) // 2)
        y = top + max(0, (screen_height - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")


    def _restore_window_size(self, value: str) -> None:
        match = re.fullmatch(r"(\d+)x(\d+)", value.strip())
        if match is None:
            return
        screen_width, screen_height = self._available_screen_size()
        max_width = max(640, screen_width - 20)
        max_height = max(560, screen_height - 20)
        width = min(max(int(match.group(1)), 800), max_width)
        height = min(max(int(match.group(2)), 600), max_height)
        self._center_window(width, height)


    def _install_file_drops(self) -> None:
        if os.name != "nt" or self.file_drop_bindings:
            return
        self.update_idletasks()
        self._install_file_drop_target()


    def _install_file_drop_target(self) -> None:
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        hwnd = self.winfo_id()

        class DropPoint(ctypes.Structure):
            _fields_ = (
                ("x", ctypes.c_long),
                ("y", ctypes.c_long),
            )

        window_proc_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_size_t,
            ctypes.c_ssize_t,
        )
        user32.GetWindowLongPtrW.argtypes = (ctypes.c_void_p, ctypes.c_int)
        user32.GetWindowLongPtrW.restype = ctypes.c_void_p
        user32.SetWindowLongPtrW.argtypes = (
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
        )
        user32.SetWindowLongPtrW.restype = ctypes.c_void_p
        user32.CallWindowProcW.argtypes = (
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_size_t,
            ctypes.c_ssize_t,
        )
        user32.CallWindowProcW.restype = ctypes.c_ssize_t
        shell32.DragAcceptFiles.argtypes = (ctypes.c_void_p, ctypes.c_int)
        shell32.DragQueryFileW.argtypes = (
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_wchar_p,
            ctypes.c_uint,
        )
        shell32.DragQueryFileW.restype = ctypes.c_uint
        shell32.DragQueryPoint.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(DropPoint),
        )
        shell32.DragQueryPoint.restype = ctypes.c_int
        shell32.DragFinish.argtypes = (ctypes.c_void_p,)
        original_wndproc = user32.GetWindowLongPtrW(hwnd, -4)
        if not original_wndproc:
            return

        def file_drop_wndproc(window, message, wparam, lparam):
            if message == 0x0233:
                try:
                    point = DropPoint()
                    inside_client = bool(
                        shell32.DragQueryPoint(wparam, ctypes.byref(point))
                    )
                    count = shell32.DragQueryFileW(wparam, 0xFFFFFFFF, None, 0)
                    values = []
                    for index in range(count):
                        length = shell32.DragQueryFileW(wparam, index, None, 0)
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        copied = shell32.DragQueryFileW(
                            wparam,
                            index,
                            buffer,
                            length + 1,
                        )
                        if copied:
                            values.append(buffer.value)
                    if inside_client and values:
                        self.file_drop_queue.put(
                            ("drop", point.x, point.y, tuple(values))
                        )
                except Exception as exc:
                    self.file_drop_queue.put(
                        (
                            "warning",
                            "无法读取拖放内容，请使用“选择…”按钮。",
                            repr(exc),
                        )
                    )
                finally:
                    try:
                        shell32.DragFinish(wparam)
                    except Exception:
                        pass
                return 0
            return user32.CallWindowProcW(
                original_wndproc, window, message, wparam, lparam
            )

        callback = window_proc_type(file_drop_wndproc)
        previous = user32.SetWindowLongPtrW(
            hwnd, -4, ctypes.cast(callback, ctypes.c_void_p)
        )
        if not previous:
            return
        self.file_drop_bindings.append((hwnd, int(previous), callback))
        shell32.DragAcceptFiles(hwnd, 1)


    def _poll_file_drop_queue(self) -> None:
        try:
            while True:
                event = self.file_drop_queue.get_nowait()
                if event[0] == "warning":
                    self._show_drop_warning(event[1])
                    if len(event) > 2:
                        self.append_log(f"拖放读取失败：{event[2]}")
                elif event[0] == "drop":
                    self._dispatch_file_drop(event[1], event[2], event[3])
        except queue.Empty:
            pass
        try:
            self.after(50, self._poll_file_drop_queue)
        except tk.TclError:
            pass


    def _dispatch_file_drop(
        self,
        client_x: int,
        client_y: int,
        values: tuple[str, ...],
    ) -> None:
        if self.busy:
            return
        try:
            screen_x = self.winfo_rootx() + client_x
            screen_y = self.winfo_rooty() + client_y
            targets = (
                (self.project_entry, self._apply_dropped_project),
                (self.entry_combo, self._apply_dropped_entry),
            )
            for widget, handler in targets:
                left = widget.winfo_rootx()
                top = widget.winfo_rooty()
                if (
                    widget.winfo_ismapped()
                    and left <= screen_x < left + widget.winfo_width()
                    and top <= screen_y < top + widget.winfo_height()
                ):
                    handler(values)
                    return
        except tk.TclError:
            return


    def _restore_file_drops(self) -> None:
        if os.name != "nt" or not self.file_drop_bindings:
            return
        shell32 = ctypes.windll.shell32
        user32 = ctypes.windll.user32
        for hwnd, original_wndproc, _ in reversed(self.file_drop_bindings):
            shell32.DragAcceptFiles(hwnd, 0)
            user32.SetWindowLongPtrW(
                hwnd,
                -4,
                original_wndproc,
            )
        self.file_drop_bindings.clear()


    def _show_drop_warning(self, message: str) -> None:
        try:
            messagebox.showwarning(APP_NAME, message, parent=self)
        except tk.TclError:
            pass


    def _single_dropped_path(self, values: tuple[str, ...]) -> Path | None:
        if len(values) != 1:
            self._show_drop_warning("一次只能拖入一个文件夹或文件。")
            return
        value = values[0].strip()
        if not value:
            self._show_drop_warning("拖放内容为空，请重新选择。")
            return None
        try:
            return Path(value).expanduser().resolve(strict=True)
        except (OSError, RuntimeError, ValueError):
            self._show_drop_warning("拖入的路径无效或已不存在。")
            return None


    def _apply_dropped_project(self, values: tuple[str, ...]) -> None:
        path = self._single_dropped_path(values)
        if path is None:
            return
        try:
            if not path.is_dir():
                self._show_drop_warning(
                    "项目目录输入框只接收文件夹；Python 脚本请拖到入口文件框。"
                )
                return
            self._set_project_directory(path)
        except (OSError, RuntimeError, ValueError, tk.TclError):
            self._show_drop_warning("无法打开这个项目文件夹，请检查路径和权限。")


    def _apply_dropped_entry(self, values: tuple[str, ...]) -> None:
        path = self._single_dropped_path(values)
        if path is None:
            return
        try:
            if not path.is_file() or path.suffix.casefold() != ".py":
                self._show_drop_warning("入口文件框只接收单个 .py 文件。")
                return
            project = path.parent
            self._activate_project(project)
            self.entry_combo["values"] = (path.name,)
            self.entry_var.set(path.name)
            self._set_name_from_entry(force=True)
            self.notebook.select(self.project_tab)
            self.append_log(
                f"已从入口文件识别项目目录：{project}；入口：{path.name}"
            )
        except (OSError, RuntimeError, ValueError, tk.TclError):
            self._show_drop_warning("无法使用这个 Python 入口文件，请检查路径和权限。")


    def _set_project_directory(self, project: Path) -> None:
        self._activate_project(project.resolve())
        self.refresh_entries()
        self.notebook.select(self.project_tab)


    def _activate_project(self, project: Path) -> None:
        if self.busy:
            return
        project = project.resolve()
        if self.active_project_path == project:
            self.project_var.set(str(project))
            return
        if self.active_project_path is not None:
            self._save_project_settings(self.active_project_path)
        self.active_project_path = project
        self.project_var.set(str(project))
        self._reset_project_settings(project)
        self._load_project_settings(project)
        self._save_global_settings()


    def _task_started(self, title):
        self.notebook.select(self.log_tab)


    def _build_log_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        toolbar = ttk.Frame(tab)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(0, weight=1)
        icon_button(toolbar, "clear", "清空日志", self.clear_log).grid(
            row=0, column=1, sticky="e"
        )
        self.log_text = RoundedText(
            tab,
            wrap="word",
            state="disabled",
            font=("Consolas", 9),
        )
        self.log_text.grid(row=1, column=0, sticky="nsew")
        text_scrollbar(tab, self.log_text, row=1)


    def choose_project(self) -> None:
        initial = self.project_var.get().strip() or str(Path.home())
        selected = filedialog.askdirectory(title="选择 Python 项目目录", initialdir=initial)
        if not selected:
            return
        self._set_project_directory(Path(selected).resolve())


    def choose_entry(self) -> None:
        project = self._project_path(required=False)
        selected = filedialog.askopenfilename(
            title="选择入口文件",
            initialdir=str(project or Path.home()),
            filetypes=(("Python 文件", "*.py"), ("所有文件", "*.*")),
        )
        if not selected:
            return
        selected_path = Path(selected).resolve()
        if project is None or project not in selected_path.parents:
            project = selected_path.parent
            self._set_project_directory(project)
        self.entry_var.set(os.path.relpath(selected_path, project))
        self._set_name_from_entry(force=True)


    def choose_icon(self) -> None:
        project = self._project_path(required=False)
        selected = filedialog.askopenfilename(
            title="选择 Windows 图标",
            initialdir=str(project or Path.home()),
            filetypes=(("Windows 图标", "*.ico"), ("所有文件", "*.*")),
        )
        if selected:
            self.icon_input_var.set(selected)


    def show_emoji_picker(self):
        if self.busy:
            return
        picker = getattr(self, 'emoji_picker_window', None)
        if picker is not None and picker.winfo_exists():
            picker.deiconify()
            picker.lift()
            picker.search_entry.focus_set()
            return
        self.emoji_picker_window = EmojiPicker(self, self._choose_emoji)

    def _queue_icon_preview(self, *_):
        if self._preview_job is not None:
            self.after_cancel(self._preview_job)
            self._preview_job = None
        self.preview_service.cancel('main-icon')
        self.icon_preview_canvas.itemconfigure(self.icon_preview_item, image='')
        self.icon_preview_canvas.itemconfigure(self.icon_preview_placeholder, state='normal', text='预览')
        self.icon_preview_image = None
        filename, text = self._icon_values()
        if filename:
            project = self.active_project_path or Path(self.project_var.get() or ".")
            source = project / Path(filename).expanduser()
            self.icon_preview_status.set('')
            self.icon_preview_canvas.itemconfigure(self.icon_preview_placeholder, text='ICO')
        elif not text:
            self.icon_preview_status.set('')
            return
        elif len(text) > 32 or any(ord(ch) < 32 for ch in text):
            self.icon_preview_status.set('请输入 1～32 个可见字符，不支持换行。')
            return
        else:
            source = text
            self.icon_preview_status.set('')
        self._preview_job = self.after(250, lambda: self._request_icon_preview(source))

    def _request_icon_preview(self, source):
        self._preview_job = None
        def ready(png, error):
            if error:
                self.icon_preview_canvas.itemconfigure(self.icon_preview_placeholder, text='!')
                self.icon_preview_status.set('无法预览：' + error)
                return
            if png is None:
                return
            self.icon_preview_image = tk.PhotoImage(master=self, data=png)
            self.icon_preview_canvas.itemconfigure(self.icon_preview_item, image=self.icon_preview_image)
            self.icon_preview_canvas.itemconfigure(self.icon_preview_placeholder, state='hidden')
            self.icon_preview_status.set('')
        self.preview_service.request('main-icon', source, 48, ready, priority=True)

    def destroy(self):
        picker = getattr(self, 'emoji_picker_window', None)
        if picker is not None and picker.winfo_exists():
            picker.destroy()
        if getattr(self, '_preview_job', None) is not None:
            self.after_cancel(self._preview_job)
            self._preview_job = None
        service = getattr(self, 'preview_service', None)
        if service is not None and not service.closed:
            service.close()
        if hasattr(self, 'file_drop_bindings'):
            self._restore_file_drops()
        if hasattr(self, "chrome"):
            self.chrome.detach()
        super().destroy()

    def _choose_emoji(self, emoji: str) -> None:
        if self.busy:
            return
        self.icon_input_var.set(emoji)
        picker = getattr(self, "emoji_picker_window", None)
        if picker is not None and picker.winfo_exists():
            picker.destroy()
        self.icon_entry.focus_set()
        self.icon_entry.icursor("end")


    def _icon_values(self) -> tuple[str, str]:
        raw = self.icon_input_var.get().strip()
        path = raw
        for left, right in (('"', '"'), ("'", "'"), ('“', '”')):
            if raw.startswith(left) and raw.endswith(right):
                path = raw[1:-1].strip()
                break
        if path.casefold().endswith('.ico'):
            return path, ""
        return "", raw

    def _set_icon_values(self, path, text):
        self.icon_input_var.set(text if text.strip() else path)


    def choose_output_directory(self) -> None:
        project = self._project_path(required=False)
        initial = self.dist_var.get().strip() or str(project or Path.home())
        selected = filedialog.askdirectory(title="选择输出目录", initialdir=initial)
        if selected:
            self.dist_var.set(selected)


    def refresh_entries(self) -> None:
        project = self._project_path(required=True)
        if project is None:
            return
        if self.active_project_path != project:
            self._activate_project(project)
        entries: list[Path] = []
        try:
            for root, dirs, files in os.walk(project):
                dirs[:] = [directory for directory in dirs if directory not in SKIP_DIRS]
                root_path = Path(root)
                entries.extend(
                    root_path / filename
                    for filename in files
                    if filename.lower().endswith(".py")
                )
                if len(entries) >= 500:
                    entries = entries[:500]
                    break
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"扫描入口文件失败：\n{exc}")
            return

        def entry_score(path: Path) -> tuple[int, int, int, str]:
            relative = path.relative_to(project)
            return (
                ENTRY_PRIORITIES.get(path.name.lower(), 100),
                len(relative.parts),
                len(str(relative)),
                str(relative).lower(),
            )

        entries.sort(key=entry_score)
        relative_entries = [str(path.relative_to(project)) for path in entries]
        self.entry_combo["values"] = relative_entries
        if self.entry_var.get().strip() not in relative_entries:
            self.entry_var.set(relative_entries[0] if relative_entries else "")
        self._set_name_from_entry()
        self.append_log(f"扫描到 {len(relative_entries)} 个 Python 文件。")


    def _entry_selected(self, _event=None) -> None:
        self._set_name_from_entry(force=True)


    def _set_name_from_entry(self, force: bool = False) -> None:
        entry = self.entry_var.get().strip()
        if entry and (force or not self.output_name_var.get().strip()):
            self.output_name_var.set(Path(entry).stem)


    def _project_path(self, required: bool = True) -> Path | None:
        value = self.project_var.get().strip().strip('"')
        if not value:
            if required:
                messagebox.showwarning(APP_NAME, "请先选择项目目录。")
            return None
        path = Path(value).expanduser().resolve()
        if not path.is_dir():
            if required:
                messagebox.showerror(APP_NAME, f"项目目录不存在：\n{path}")
            return None
        if self.active_project_path != path:
            self._activate_project(path)
        return path


    def check_uv(self) -> bool:
        self.uv_path = locate_uv()
        if self.uv_path is None:
            self.uv_status_var.set("未找到 uv")
            return False
        try:
            result = subprocess.run(
                [str(self.uv_path), "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            version = (result.stdout or result.stderr).strip()
            self.uv_status_var.set(version.split(' (', 1)[0] or 'uv 已就绪')
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError) as exc:
            self.uv_status_var.set("uv 检查失败")
            self.append_log(f"uv 检查失败：{exc}")
            return False


    def install_uv(self) -> None:
        if os.name != "nt":
            messagebox.showinfo(APP_NAME, "请按 uv 官方文档安装：https://docs.astral.sh/uv/")
            return
        if not messagebox.askyesno(
            APP_NAME,
            "将调用 Astral 官方脚本下载并安装 uv。\n\n"
            "来源：https://astral.sh/uv/install.ps1\n\n是否继续？",
        ):
            return
        powershell = shutil.which("powershell") or "powershell.exe"
        command = [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "irm https://astral.sh/uv/install.ps1 | iex",
        ]
        self._run_task(
            "安装 uv",
            [("运行 Astral 官方 uv 安装脚本", command, Path.cwd())],
            on_success=self.check_uv,
        )


    def generate_dependencies(self) -> None:
        if self.busy:
            return
        project = self._project_path(required=True)
        if project is None:
            return
        output_value = DEFAULT_REQUIREMENTS_NAME
        try:
            output_path, redirected = dependency_output_path(project, output_value)
        except ValueError as exc:
            messagebox.showerror(APP_NAME, str(exc))
            return
        if redirected:
            self.append_log(
                f"{Path(output_value).name} 是手写的依赖文件，不覆盖；"
                f"本次结果写入 {output_path.name}"
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        needs_uv = self.dependency_mode_var.get() == LOCKED_DEPENDENCY_MODE
        if needs_uv and not self._ensure_uv():
            return
        entry = self._entry_path(project)
        if entry is None:
            return
        scan_target = output_path.with_suffix(".in") if needs_uv else output_path
        if scan_target.exists() and not is_generated_requirements(scan_target):
            messagebox.showerror(APP_NAME, f"不会覆盖手写依赖文件：{scan_target}")
            return
        try:
            file_count, unreadable = scan_local_requirements(project, entry, scan_target)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"本地扫描失败：\n{exc}")
            return
        self.notebook.select(self.log_tab)
        self.append_log(f"本地扫描完成：从入口递归检查 {file_count} 个 Python 文件，输出 {scan_target}")
        if unreadable:
            self.append_log("以下文件无法解析，已跳过：" + "、".join(unreadable[:10]))

        def dependency_done() -> None:
            if needs_uv and output_path.is_file() and not is_generated_requirements(output_path):
                output_path.write_text(GENERATED_REQUIREMENTS_MARKER + '\n' + output_path.read_text(encoding='utf-8-sig'), encoding='utf-8')
            self.requirements_var.set(str(output_path))
            self._save_project_settings(project)
            self.notebook.select(self.project_tab)
            self.append_log(f"依赖文件已生成：{output_path}")
            note = (
                f"\n\n原来的 {Path(output_value).name} 是手写文件，已保留未改动。"
                if redirected
                else ""
            )
            messagebox.showinfo(
                APP_NAME,
                f"依赖文件已生成：\n{output_path}{note}\n\n可在打包页点击查看图标打开文件。",
            )

        if needs_uv:
            command = [
                str(self.uv_path), "pip", "compile", str(scan_target),
                "--output-file", str(output_path), "--no-header",
            ]
            if not getattr(sys, "frozen", False):
                command.extend(["--python-version", f"{sys.version_info.major}.{sys.version_info.minor}"])
            self._run_task("生成依赖", [("解析并锁定依赖版本", command, project)], on_success=dependency_done)
        else:
            dependency_done()


    def view_requirements(self) -> None:
        project = self._project_path(required=True)
        if project is None:
            return
        path = self._requirements_path(project)
        if path is None:
            return
        if not path.is_file():
            messagebox.showinfo(APP_NAME, "尚未生成依赖文件，请先点击扫描图标。")
            return
        self._open_path(path)


    def open_uv_cache(self) -> None:
        if not self._ensure_uv():
            return
        path = uv_cache_directory(self.uv_path, self._project_path(required=False))
        if path is None:
            messagebox.showwarning(APP_NAME, "未能获取 uv 缓存目录。")
            return
        if not path.is_dir():
            messagebox.showinfo(APP_NAME, f"uv 尚未创建缓存目录：\n{path}")
            return
        self._open_path(path)


    def _ensure_uv(self) -> bool:
        if self.uv_path is not None and self.uv_path.is_file():
            return True
        if self.check_uv():
            return True
        messagebox.showwarning(
            APP_NAME, "未找到 uv。请在“打包”页点击下载图标安装 uv，再点击刷新图标检查版本。"
        )
        return False


    def _update_dependency_action_state(self, *_args) -> None:
        system_mode = self._is_system_python_mode()
        state = "disabled" if system_mode or self.busy else "normal"
        tools_state = "disabled" if self.busy else "normal"
        self.dependency_generate_button.configure(state=tools_state)
        self.check_uv_button.configure(state=tools_state)
        self.install_uv_button.configure(state=tools_state)
        self.preset_combo.configure(state="disabled" if state == "disabled" else "readonly")
        for control in (self.clean_checkbox, self.exclude_dev_checkbox, self.collect_data_checkbox,
                        self.hidden_imports_entry, self.excludes_entry, self.extra_args_text):
            control.configure(state=state)

    def start_build(self) -> None:
        if self._is_system_python_mode():
            self._start_system_launcher_build()
            return
        result = self._build_command()
        if result is None:
            return
        command, project, dist = result
        dist.mkdir(parents=True, exist_ok=True)
        (project / ".uv-packager").mkdir(parents=True, exist_ok=True)
        delete_work_cache = self.delete_cache_after_build_var.get()
        self._save_settings()

        def build_done() -> None:
            self.append_log(f"打包完成，输出目录：{dist}")
            cleanup_warning = None
            if delete_work_cache:
                cleanup_warning = self._delete_build_work_cache(
                    project,
                    system_launcher=False,
                    protected_path=dist,
                )
            self._open_path(dist)
            if cleanup_warning:
                messagebox.showwarning(APP_NAME, cleanup_warning)

        self._run_task(
            "打包项目",
            [(self.build_environment, command, project)],
            on_success=build_done,
        )


    def _start_system_launcher_build(self) -> None:
        settings = self._system_launcher_settings()
        if settings is None:
            return
        settings.dist.mkdir(parents=True, exist_ok=True)
        delete_work_cache = self.delete_cache_after_build_var.get()
        self._save_settings()

        def operation() -> None:
            build_system_python_launcher(
                project=settings.project,
                entry=settings.entry,
                output=settings.output,
                title=settings.name,
                console=settings.console,
                source_only=settings.source_only,
                entry_only=settings.entry_only,
                icon_path=settings.icon,
                log=lambda text: self.task_queue.put(("log", text)),
                cancelled=lambda: self.cancel_requested,
            )

        def build_done() -> None:
            self.append_log(f"打包完成，输出文件：{settings.output}")
            cleanup_warning = None
            if delete_work_cache:
                cleanup_warning = self._delete_build_work_cache(
                    settings.project,
                    system_launcher=True,
                    protected_path=settings.output,
                )
            self._open_path(settings.dist)
            if cleanup_warning:
                messagebox.showwarning(APP_NAME, cleanup_warning)

        self._run_callable_task(
            "生成系统 Python 启动器",
            operation,
            on_success=build_done,
        )


    def stop_task(self) -> None:
        worker_active = bool(self.worker_thread and self.worker_thread.is_alive())
        if not worker_active:
            return
        if not messagebox.askyesno(APP_NAME, "确定停止当前任务吗？"):
            return
        self.task_status_var.set("正在停止…")
        self.build_button.configure(state="disabled")
        self.cancel_task()

    def _poll_task_queue(self) -> None:
        try:
            while True:
                event = self.task_queue.get_nowait()
                if event[0] == "log":
                    self.append_log(event[1])
                elif event[0] == "done":
                    success = bool(event[1])
                    message = str(event[2])
                    reason = event[3] if len(event) > 3 else ""
                    self._set_busy(False, "就绪" if success else message)
                    self.append_log(f"\n{message}")
                    callback = self.task_success_callback
                    self.task_success_callback = None
                    if success and callback:
                        try:
                            callback()
                        except (OSError, ValueError) as exc:
                            self.append_log(f'任务后处理失败：{exc}')
                            messagebox.showerror(APP_NAME, f'任务已执行，但后处理失败：\n{exc}')
                    elif not success and reason == "error":
                        messagebox.showerror(
                            APP_NAME,
                            f"任务失败：\n{message}\n\n请查看“日志”页签。",
                        )
        except queue.Empty:
            pass
        self.after(100, self._poll_task_queue)


    def _set_busy(self, busy: bool, status: str) -> None:
        self.busy = busy
        if busy:
            picker = getattr(self, 'emoji_picker_window', None)
            if picker is not None and picker.winfo_exists():
                picker.destroy()
        # Freeze project controls so task callbacks cannot write to another project.
        if busy:
            self._saved_widget_states = []
            def freeze(widget):
                for child in widget.winfo_children():
                    if isinstance(child, (ttk.Entry, ttk.Combobox, ttk.Button, ttk.Checkbutton, ttk.Radiobutton)):
                        self._saved_widget_states.append((child, str(child.cget('state'))))
                        child.configure(state='disabled')
                    freeze(child)
            freeze(self.project_tab)
        else:
            for widget, old_state in getattr(self, '_saved_widget_states', []):
                widget.configure(state=old_state)
        self._update_dependency_action_state()
        self.task_status_var.set(status)
        self.build_button.configure(text="停止任务" if busy else "开始打包",
                                    command=self.stop_task if busy else self.start_build, state="normal")
        if busy:
            self.progress.grid()
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.grid_remove()


    def append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


    def clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


    def _open_path(self, path: Path) -> None:
        try:
            if os.name == "nt":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"无法打开：\n{path}\n\n{exc}")


    def _apply_project_defaults(self, project: Path) -> None:
        self.dependency_mode_var.set(FAST_DEPENDENCY_MODE)
        self.requirements_var.set(str(project / DEFAULT_REQUIREMENTS_NAME))
        self.dist_var.set(str(project / "dist"))

    def _apply_project_settings_data(self, data: dict) -> None:
        project = self.active_project_path
        selected = data.get("requirements")
        # Only the generated sibling may override the default in the GUI.
        # It is used when generating beside a handwritten default file.
        fallback = project / "runtime-requirements.generated.txt"
        current = project / DEFAULT_REQUIREMENTS_NAME
        if isinstance(selected, str) and (project / selected) == fallback and fallback.is_file():
            current = fallback
        # The GUI uses the default interpreter and PyInstaller version for all projects.
        # The CLI can still accept explicitly requested versions.
        settings = {**data, "requirements": str(current)}
        settings.pop("python_version", None)
        settings.pop("pyinstaller_version", None)
        super()._apply_project_settings_data(settings)

    def _load_project_settings(self, project: Path) -> bool:
        path = project_settings_path(APP_DIR, project)
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError, UnicodeError):
            return False
        if not isinstance(data, dict):
            return False
        self._apply_project_settings_data(data)
        return True


    def _save_project_settings(self, project: Path | None = None) -> bool:
        project = project or self.active_project_path
        if project is None or not project.is_dir():
            return False
        icon_path, icon_text = self._icon_values()
        data = {
            "settings_version": 1,
            "project_directory": str(project),
            "entry": self.entry_var.get(),
            "output_name": self.output_name_var.get(),
            "icon": self._portable_project_value(project, icon_path),
            "icon_text": icon_text,
            "dist": self._portable_project_value(project, self.dist_var.get()),
            "package_mode": self.package_mode_var.get(),
            "window_mode": self.window_mode_var.get(),
            "preset": self.preset_var.get(),
            "clean": self.clean_var.get(),
            "delete_cache_after_build": self.delete_cache_after_build_var.get(),
            "requirements": self._portable_project_value(
                project, self.requirements_var.get()
            ),
            "hidden_imports": self.hidden_imports_var.get(),
            "excludes": self.excludes_var.get(),
            "exclude_dev": self.exclude_dev_var.get(),
            "auto_collect_data": self.auto_collect_data_var.get(),
            "extra_args": self.extra_args_text.get("1.0", "end").strip(),
        }
        path = project_settings_path(APP_DIR, project)
        temporary: Path | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             prefix=f".{path.stem}-", suffix=".tmp", delete=False) as file:
                temporary = Path(file.name)
                json.dump(data, file, ensure_ascii=False, indent=2)
            temporary.replace(path)
            return True
        except OSError as exc:
            self.append_log(f"无法保存项目打包配置：{path}\n{exc}")
            return False
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass


    def _load_settings(self) -> None:
        source = self.config_path
        if not source.exists():
            source = Path(os.environ.get('APPDATA', Path.home())) / 'UvPackagerGUI' / 'settings.json'
        try:
            data = json.loads(source.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError, UnicodeError):
            data = {}
        if not isinstance(data, dict):
            data = {}

        window_size = data.get("window_size")
        if isinstance(window_size, str):
            self._restore_window_size(window_size)

        project_value = data.get("last_project") or data.get("project")
        if not isinstance(project_value, str) or not project_value.strip():
            return
        project = Path(project_value).expanduser().resolve()
        self.project_var.set(str(project))
        if not project.is_dir():
            return

        self.active_project_path = project
        self._reset_project_settings(project)
        loaded = self._load_project_settings(project)
        if not loaded and str(data.get("settings_version", 1)).isdigit() and int(data.get("settings_version", 1)) <= 10:
            self._apply_project_settings_data(data)
            self._save_project_settings(project)
        self.refresh_entries()


    def _save_global_settings(self) -> None:
        data = {
            "settings_version": 11,
            "window_size": f"{self.winfo_width()}x{self.winfo_height()}",
            "last_project": str(self.active_project_path or ""),
        }
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass


    def _save_settings(self) -> None:
        self._save_project_settings()
        self._save_global_settings()


    def _on_close(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            if not messagebox.askyesno(APP_NAME, "任务仍在运行，确定退出吗？"):
                return
            self.cancel_task()
            self.after(100, self._finish_close)
            return
        self._finish_close()

    def _finish_close(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.after(100, self._finish_close)
            return
        self._save_settings()
        self.destroy()


def launch_gui():
    tkwebui.enable_dpi_awareness()
    PackagerApp().mainloop()
