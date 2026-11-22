"""Compact TkWebUI layouts with wrapping text and scrollable settings."""
import tkinter as tk
from tkinter import font as tkfont, ttk
from packager_core import (
    APP_VERSION,
    FAST_DEPENDENCY_MODE,
    LOCKED_DEPENDENCY_MODE,
    SYSTEM_PYTHON_ENTRY_ONLY_MODE,
    SYSTEM_PYTHON_PACKAGE_MODE,
    SYSTEM_PYTHON_SOURCE_ONLY_MODE,
)
import tkwebui
from native_icon import png_bytes
from tkwebui import PALETTE, ScrollArea, ThemedCombobox, RoundedText


# Segoe MDL2 Assets is part of Windows 10 and 11.
ICON_GLYPHS = {
    "folder": "\ue8b7", "file": "\ue8e5", "refresh": "\ue72c",
    "emoji": "\ue76e", "preview": "\ue890",
    "scan": "\ue8fe", "download": "\ue896", "clear": "\ue74d",
    "back": "\ue76b", "next": "\ue76c",
}


def icon_button(parent, icon, label, command):
    button = ttk.Button(parent, text=ICON_GLYPHS[icon], command=command,
                        style="ActionIcon.TButton", width=0)
    tip = tkwebui.Tooltip(button, label)
    button.bind("<FocusIn>", tip.schedule, add="+")
    button.bind("<FocusOut>", tip.hide, add="+")
    return button


def text_scrollbar(parent, text, row=0):
    bar = ttk.Scrollbar(parent, command=text.yview)
    bar.grid(row=row, column=1, sticky="ns")

    def update(first, last):
        bar.set(first, last)
        if float(first) <= 0 and float(last) >= 1:
            bar.grid_remove()
        else:
            bar.grid()

    text.configure(yscrollcommand=update)


def configure_rounded_switch(root, style):
    scale = root.winfo_fpixels("1i") / 96
    width, height = round(32 * scale), round(20 * scale)
    background = bytes.fromhex(PALETTE["bg"].lstrip("#"))
    thumb = bytes.fromhex("ffffff")
    images = {}
    for selected, disabled, fill in (
        (False, False, "#8B93A0"),
        (True, False, PALETTE["accent"]),
        (False, True, "#E0E3E9"),
        (True, True, "#AFCBEA"),
    ):
        track = bytes.fromhex(fill.lstrip("#"))
        center = 23 if selected else 9

        def sample(x, y):
            x, y = x / scale, y / scale
            if (x - center) ** 2 + (y - 10) ** 2 <= 5.5 ** 2:
                return thumb
            if (x - min(23, max(9, x))) ** 2 + (y - 10) ** 2 <= 8 ** 2:
                return track
            return background

        rgba = bytearray()
        for y in range(height):
            for x in range(width):
                colors = [sample(x + dx, y + dy) for dx, dy in ((.25, .25), (.25, .75), (.75, .25), (.75, .75))]
                rgba.extend(sum(channel) // 4 for channel in zip(*colors))
                rgba.append(255)
        images[selected, disabled] = tk.PhotoImage(master=root, data=png_bytes(width, height, rgba))

    root._rounded_switch_images = images
    style.element_create("RoundedSwitch.indicator", "image", images[False, False],
                         ("disabled selected", images[True, True]), ("disabled", images[False, True]),
                         ("selected", images[True, False]))
    style.layout("Rounded.Switch.TCheckbutton", [("Checkbutton.padding", {"sticky": "nsew", "children": [
        ("RoundedSwitch.indicator", {"side": "left"}),
        ("Checkbutton.label", {"side": "left", "sticky": "w"}),
    ]})])
    style.configure("Rounded.Switch.TCheckbutton", background=PALETTE["bg"])
    style.map("Rounded.Switch.TCheckbutton",
              background=[("active", PALETTE["bg"])],
              foreground=[("disabled", PALETTE["disabled"]), ("focus", PALETTE["accent"])])


def text_hint(widget, message):
    """Display a hint without inserting it into the argument text."""
    label = ttk.Label(widget.container, text=message, style="Subheader.TLabel")

    def refresh(_event=None):
        if widget.focus_get() is widget or widget.get("1.0", "end-1c"):
            label.place_forget()
        else:
            label.place(in_=widget, x=0, y=0)

    def modified(_event):
        if widget.edit_modified():
            widget.edit_modified(False)
            refresh()

    label.bind("<Button-1>", lambda _: widget.focus_set())
    widget.bind("<FocusIn>", refresh, add="+")
    widget.bind("<FocusOut>", refresh, add="+")
    widget.bind("<<Modified>>", modified, add="+")
    refresh()


class PackagerChrome(tkwebui.WindowChrome):
    def window_proc(self, hwnd, message, wparam, lparam):
        # Block legacy non-DWM titlebar/frame painting (WM_NCUAHDRAWCAPTION /
        # WM_NCUAHDRAWFRAME) triggered by DefWindowProc on WM_SETICON/WM_SETTEXT.
        if message in (0x00AE, 0x00AF):
            return 0
        return super().window_proc(hwnd, message, wparam, lparam)

    def close(self):
        # Cancellation of the close dialog must leave the drag handlers attached.
        # PackagerApp.destroy detaches the chrome after closing is confirmed.
        self.close_action()


class LayoutMixin:
    def _configure_style(self):
        tkwebui.apply_theme(self, font_size=9)
        self.label_column_width = tkfont.nametofont("TkDefaultFont").measure("打包模式") + 12
        style = ttk.Style(self)
        configure_rounded_switch(self, style)
        style.configure('Subheader.TLabel', foreground=PALETTE['muted'])
        style.configure("Advanced.Quiet.TButton", anchor="w", padding=(6, 6))
        style.configure("ActionIcon.TButton", font=("Segoe MDL2 Assets", 12), padding=(9, 6))
        style.configure('Emoji.TEntry', font=('Segoe UI Emoji', 10))
        style.configure('EmojiPicker.TButton', font=('Segoe UI Emoji', 13), padding=3)

    def _build_ui(self):
        outer = ttk.Frame(self)
        outer.pack(fill='both', expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)
        self.titlebar = ttk.Frame(outer, padding=("10p", "5p", "10p", 0))
        self.titlebar.grid(row=0, column=0, sticky="ew")
        title = ttk.Label(self.titlebar, text=f"Python 精简打包  {APP_VERSION}", image=self.window_icon_image,
                          compound="left", padding=(0, 2, 6, 2))
        title.pack(side="left")
        self.chrome = PackagerChrome(self, self.titlebar, drag_widgets=(self.titlebar, title), on_close=self._on_close)
        self.notebook = ttk.Notebook(outer)
        self.notebook.grid(row=1, column=0, sticky='nsew', padx='10p', pady=(6, 0))
        self.project_tab = ttk.Frame(self.notebook, padding=10)
        self.log_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.project_tab, text="打包")
        self.notebook.add(self.log_tab, text="日志")
        self.project_scroll = ScrollArea(self.project_tab)
        self.project_scroll.pack(fill="both", expand=True)
        self._build_project_tab(self.project_scroll.body)
        self._build_log_tab(self.log_tab)
        footer = ttk.Frame(outer, padding=(0, 6, 0, 0))
        footer.grid(row=2, column=0, sticky='ew', padx='10p', pady=(0, '10p'))
        footer.columnconfigure(0, weight=1)
        actions = ttk.Frame(footer)
        actions.grid(row=1, column=0, sticky='ew')
        actions.columnconfigure(0, weight=1)
        task_label = ttk.Label(actions, textvariable=self.task_status_var, width=12)
        task_label.grid(row=0, column=0, sticky='w')
        self.progress = ttk.Progressbar(footer, mode='indeterminate', length=120)
        self.progress.grid(row=2, column=0, sticky='ew', pady=(5, 0))
        self.build_button = ttk.Button(actions, text="开始打包", command=self.start_build, style="Primary.TButton")
        self.build_button.grid(row=0, column=1, sticky="e")
        self.progress.grid_remove()

    def _build_project_tab(self, tab):
        tab.columnconfigure(0, minsize=self.label_column_width)
        tab.columnconfigure(1, weight=1)
        def label(text, row):
            ttk.Label(tab, text=text).grid(row=row, column=0, sticky='w', padx=(0, 10), pady=4)
        def entry(variable, row):
            field = ttk.Entry(tab, textvariable=variable, width=1)
            field.grid(row=row, column=1, sticky='ew', pady=4)
            return field
        def button(icon, label, command, row):
            icon_button(tab, icon, label, command).grid(row=row, column=2, padx=(8, 0), pady=4, sticky='w')
        label('项目目录', 0)
        self.project_entry = entry(self.project_var, 0)
        button('folder', '选择项目目录', self.choose_project, 0)
        label('入口文件', 1)
        self.entry_combo = ThemedCombobox(tab, textvariable=self.entry_var, width=1)
        self.entry_combo.grid(row=1, column=1, sticky='ew', pady=4)
        self.entry_combo.bind('<<ComboboxSelected>>', self._entry_selected)
        button('file', '选择入口文件', self.choose_entry, 1)
        icon_button(tab, 'refresh', '刷新入口列表', self.refresh_entries).grid(row=1, column=3, padx=(4, 0))
        ttk.Separator(tab, orient="horizontal").grid(row=2, column=0, columnspan=4,
                                                     sticky="ew", pady=(7, 5))
        label('打包模式', 3)
        modes = ttk.Frame(tab)
        modes.grid(row=3, column=1, columnspan=3, sticky="ew", pady=4)
        modes.columnconfigure((0, 1, 2), weight=1)
        for row, column, display, value, hint in (
            (0, 0, "独立 EXE", "单文件（--onefile）",
             "生成单个 EXE，内含 Python 和收集到的依赖。"),
            (0, 1, "独立目录", "目录模式（--onedir）",
             "生成含 Python 和依赖的程序目录，分发时带上整个目录。"),
            (1, 0, "入口包装", SYSTEM_PYTHON_ENTRY_ONLY_MODE,
             "只内置所选入口脚本，可设置 EXE 图标和控制台。\n"
             "运行时使用系统 Python，其他模块和资源放在 EXE 旁的原有相对位置。"),
            (1, 1, "启动器内置", SYSTEM_PYTHON_PACKAGE_MODE,
             "内置项目源码和资源，运行时使用目标电脑的 Python。"),
            (1, 2, "启动器外置", SYSTEM_PYTHON_SOURCE_ONLY_MODE,
             "内置项目中收集到的 Python 源码，资源留在 EXE 旁对应位置。"),
        ):
            radio = ttk.Radiobutton(modes, text=display, variable=self.package_mode_var, value=value)
            radio.grid(row=row, column=column, sticky="w", padx=(0, 12), pady=2)
            tkwebui.Tooltip(radio, hint)
        label("运行窗口", 4)
        self.window_switch = tkwebui.SquareSwitch(
            tab, text="显示控制台", variable=self.window_mode_var, style="Rounded.Switch.TCheckbutton",
            onvalue="显示命令行窗口（--console）", offvalue="不显示命令行窗口（--windowed）",
        )
        self.window_switch.grid(row=4, column=1, sticky="w", pady=4)
        tkwebui.Tooltip(self.window_switch, "打开时显示控制台，关闭时运行不弹出控制台。")
        label("生成依赖", 5)
        scans = ttk.Frame(tab)
        scans.grid(row=5, column=1, sticky="ew", pady=4)
        quick_scan = ttk.Radiobutton(scans, text="快速扫描", variable=self.dependency_mode_var,
                                     value=FAST_DEPENDENCY_MODE)
        advanced_scan = ttk.Radiobutton(scans, text="锁定版本", variable=self.dependency_mode_var,
                                        value=LOCKED_DEPENDENCY_MODE)
        quick_scan.grid(row=0, column=0, sticky="w", padx=(0, 12))
        advanced_scan.grid(row=0, column=1, sticky="w")
        tkwebui.Tooltip(quick_scan, "从入口追踪导入并生成包名清单")
        tkwebui.Tooltip(advanced_scan, "扫描后由 uv 解析并锁定直接及间接依赖版本")
        self.dependency_generate_button = icon_button(tab, 'scan', '扫描并生成依赖文件', self.generate_dependencies)
        self.dependency_generate_button.grid(row=5, column=2, sticky='w', padx=(8, 0))
        icon_button(tab, 'preview', '查看依赖文件', self.view_requirements).grid(row=5, column=3, padx=(4, 0))
        label('程序名称', 6)
        entry(self.output_name_var, 6)
        label('程序图标', 7)
        icon_box = ttk.Frame(tab)
        icon_box.grid(row=7, column=1, sticky='ew', pady=4)
        icon_box.columnconfigure(0, weight=1)
        self.icon_entry = ttk.Entry(icon_box, textvariable=self.icon_input_var, style='Emoji.TEntry', width=1)
        self.icon_entry.grid(row=0, column=0, sticky='ew')
        tkwebui.Tooltip(self.icon_entry, '输入文字、表情或 .ico 文件路径')
        self.icon_preview_canvas = tk.Canvas(icon_box, width=48, height=48, background=PALETTE['bg'],
                                             highlightthickness=1, highlightbackground=PALETTE['border'])
        self.icon_preview_canvas.grid(row=0, column=1, padx=(8, 0))
        self.icon_preview_item = self.icon_preview_canvas.create_image(24, 24, anchor='center')
        self.icon_preview_placeholder = self.icon_preview_canvas.create_text(24, 24, text='预览', fill=PALETTE['muted'], font='TkDefaultFont')
        button('file', '选择 ICO 图标文件', self.choose_icon, 7)
        icon_button(tab, 'emoji', '插入表情', self.show_emoji_picker).grid(row=7, column=3, padx=(4, 0))
        self.icon_preview_status = tk.StringVar()
        preview_note = ttk.Label(tab, textvariable=self.icon_preview_status, style='Subheader.TLabel')
        preview_note.grid(row=8, column=1, sticky='w')
        preview_note.grid_remove()
        def show_note(*_):
            if self.icon_preview_status.get():
                preview_note.grid()
            else:
                preview_note.grid_remove()
        self.icon_preview_status.trace_add('write', show_note)
        label('输出目录', 9)
        entry(self.dist_var, 9)
        button('folder', '选择输出目录', self.choose_output_directory, 9)
        label('uv', 10)
        tools = ttk.Frame(tab)
        tools.grid(row=10, column=1, sticky='ew', pady=4)
        ttk.Label(tools, textvariable=self.uv_status_var).pack(side='left', padx=(0, 11))
        self.check_uv_button = icon_button(tools, 'refresh', '检查 uv 版本', self.check_uv)
        self.check_uv_button.pack(side='left')
        self.install_uv_button = icon_button(tools, 'download', '安装 uv', self.install_uv)
        self.install_uv_button.pack(side='left', padx=4)
        icon_button(tools, 'folder', '打开 uv 缓存目录', self.open_uv_cache).pack(side='left')

        self.advanced_options = tkwebui.Accordion(tab, "高级选项", padding=8)
        self.advanced_options.grid(row=11, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        self.advanced_options.header.configure(style="Advanced.Quiet.TButton", command=self._toggle_advanced_options)
        self._build_advanced_options(self.advanced_options.body)

    @staticmethod
    def _form_row(tab, row, caption, field):
        ttk.Label(tab, text=caption).grid(row=row, column=0, sticky='w', padx=(0, 10), pady=4)
        field.grid(row=row, column=1, sticky='ew', pady=4)
        return field

    def _build_advanced_options(self, tab):
        tab.columnconfigure(0, minsize=self.label_column_width)
        tab.columnconfigure(1, weight=1)
        self.preset_combo = self._form_row(tab, 0, '打包预设',
            ThemedCombobox(tab, textvariable=self.preset_var, values=('标准（推荐）', '精简优先（排除开发工具）',
                '兼容优先（禁用 UPX）', '导入调试（输出详细信息）'), state='readonly', width=1))
        self.hidden_imports_entry = self._form_row(tab, 1, "隐藏导入", tkwebui.PlaceholderEntry(
            tab, placeholder="补上动态导入的模块，例如 plugins.loader, PIL.Image",
            textvariable=self.hidden_imports_var, width=1,
        ))
        self.excludes_entry = self._form_row(tab, 2, "排除模块", tkwebui.PlaceholderEntry(
            tab, placeholder="排除确认未使用的模块，例如 pytest, IPython",
            textvariable=self.excludes_var, width=1,
        ))
        flags = ttk.Frame(tab)
        flags.grid(row=3, column=1, sticky='w', pady=6)
        self.clean_checkbox = ttk.Checkbutton(flags, text='重新分析构建文件', variable=self.clean_var)
        self.clean_checkbox.grid(row=0, column=0, sticky='w')
        self.delete_cache_checkbox = ttk.Checkbutton(flags, text='完成后清理工作目录', variable=self.delete_cache_after_build_var)
        self.delete_cache_checkbox.grid(row=0, column=1, sticky='w', padx=(16, 0))
        self.exclude_dev_checkbox = ttk.Checkbutton(flags, text="排除常见开发工具", variable=self.exclude_dev_var)
        self.exclude_dev_checkbox.grid(row=1, column=0, sticky="w")
        self.collect_data_checkbox = ttk.Checkbutton(flags, text="自动收集资源", variable=self.auto_collect_data_var)
        self.collect_data_checkbox.grid(row=1, column=1, sticky="w", padx=(16, 0))
        for control, hint in (
            (self.clean_checkbox, "打包前清理 PyInstaller 临时文件并重新分析"),
            (self.delete_cache_checkbox, "打包成功后删除该项目的构建工作目录"),
            (self.exclude_dev_checkbox, "从包中排除 pytest、IPython、Jupyter 等常见开发工具"),
            (self.collect_data_checkbox, "收集已识别的主题、Tcl/Tk 和源码目录资源"),
        ):
            tkwebui.Tooltip(control, hint)
        ttk.Label(tab, text="附加参数").grid(row=4, column=0, sticky="nw", padx=(0, 10), pady=6)
        box = ttk.Frame(tab)
        box.grid(row=4, column=1, sticky='ew', pady=4)
        box.columnconfigure(0, weight=1)
        self.extra_args_text = RoundedText(box, height=4, width=1, wrap='word', scrollbars=False)
        self.extra_args_text.grid(row=0, column=0, sticky='ew')
        text_scrollbar(box, self.extra_args_text)
        text_hint(self.extra_args_text, "每行一个参数，例如 --collect-data=my_package")
