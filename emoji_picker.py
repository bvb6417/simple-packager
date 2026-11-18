"""Searchable, resizable, client-titlebar emoji picker."""
import math
import tkinter as tk
from tkinter import ttk
from packager_layout import icon_button
from emoji_catalog import search_emojis
from packager_core import EMOJI_LIBRARY
from tkwebui import WindowChrome, ScrollArea, ThemedCombobox, PALETTE, Tooltip


class EmojiPicker(tk.Toplevel):
    PAGE_SIZE = 40

    def __init__(self, owner, choose):
        super().__init__(owner)
        self.withdraw()
        self.owner, self.choose = owner, choose
        self.prefix = f'picker-{id(self)}-'
        self.closed = False
        self.page = 0
        self.columns = 8
        self.page_size = self.PAGE_SIZE
        self.search_job = self.resize_job = None
        self.buttons = []
        self.matches = []
        self.images = []
        self.title('插入表情')
        self.configure(background=PALETTE['bg'])
        # WindowChrome retains native minimize/maximize; no modal grab.
        width, height = min(780, owner.winfo_screenwidth()-40), min(560, owner.winfo_screenheight()-80)
        self.geometry(f'{width}x{height}+{max(0, owner.winfo_rootx()+40)}+{max(0, owner.winfo_rooty()+40)}')
        self.minsize(560, 400)
        # Keep controls clear of WindowChrome corner handles as monitor DPI increases.
        shell = ttk.Frame(self, padding="10p")
        shell.pack(fill='both', expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)
        titlebar = ttk.Frame(shell)
        titlebar.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        title = ttk.Label(titlebar, text='插入表情', padding=(4, 0))
        title.pack(side='left')
        self.chrome = WindowChrome(self, titlebar, drag_widgets=(titlebar, title), on_close=self.destroy)
        toolbar = ttk.Frame(shell)
        toolbar.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        toolbar.columnconfigure(1, weight=1)
        self.query = tk.StringVar(self)
        self.category = tk.StringVar(self, value='全部')
        ttk.Label(toolbar, text='搜索').grid(row=0, column=0, padx=(0, 8))
        self.search_entry = ttk.Entry(toolbar, textvariable=self.query, width=12)
        self.search_entry.grid(row=0, column=1, sticky='ew')
        icon_button(toolbar, 'clear', '清空搜索', lambda: self.query.set('')).grid(row=0, column=2, padx=6)
        self.category_combo = ThemedCombobox(toolbar, textvariable=self.category,
            values=('全部', *EMOJI_LIBRARY), state='readonly', width=13)
        self.category_combo.grid(row=0, column=3, sticky='ew')
        self.area = ScrollArea(shell)
        self.area.grid(row=2, column=0, sticky='nsew')
        self.area.canvas.bind('<Configure>', self._resize, add='+')
        footer = ttk.Frame(shell)
        footer.grid(row=3, column=0, sticky='ew', pady=(8, 0))
        footer.columnconfigure(0, weight=1)
        self.status = ttk.Label(footer, text='', style='Subheader.TLabel', wraplength=1, justify='left')
        self.status.grid(row=0, column=0, sticky='ew')
        self.status.bind('<Configure>', lambda e: self.status.configure(wraplength=max(40, e.width)))
        self.previous = icon_button(footer, 'back', '上一页', lambda: self.turn(-1))
        self.previous.grid(row=0, column=1, padx=3)
        self.page_label = ttk.Label(footer, text='1 / 1')
        self.page_label.grid(row=0, column=2, padx=6)
        self.next = icon_button(footer, 'next', '下一页', lambda: self.turn(1))
        self.next.grid(row=0, column=3, padx=3)
        self.query.trace_add('write', self._schedule_search)
        self.category.trace_add('write', self._schedule_search)
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.bind('<Escape>', lambda event: self.destroy())
        self.search_entry.bind('<Return>', self._choose_first)
        self.deiconify()
        self.search_entry.focus_set()
        self.search()

    def _schedule_search(self, *_):
        if self.search_job is not None:
            self.after_cancel(self.search_job)
        self.search_job = self.after(160, self.search)

    def search(self):
        self.search_job = None
        self.page = 0
        self.matches = search_emojis(self.query.get(), self.category.get())
        self._draw()

    def _resize(self, event):
        columns = max(4, min(12, event.width // 66))
        page_size = columns * max(1, min(6, event.height // 64))
        if columns != self.columns or page_size != self.page_size:
            self.columns = columns
            self.page_size = page_size
            self.page = 0
            if self.resize_job is not None:
                self.after_cancel(self.resize_job)
            self.resize_job = self.after(100, self._draw)

    def turn(self, delta):
        self.page = max(0, min(self.page+delta, max(0, math.ceil(len(self.matches)/self.page_size)-1)))
        self._draw()

    def _choose_first(self, event):
        if self.search_job is not None:
            self.after_cancel(self.search_job)
            self.search()
        if self.matches:
            self.choose(self.matches[self.page*self.page_size]['emoji'])
        return 'break'

    def _draw(self):
        if self.closed:
            return
        self.resize_job = None
        self.owner.preview_service.cancel(self.prefix)
        for child in self.area.body.winfo_children():
            child.destroy()
        self.buttons, self.images = [], []
        for col in range(12):
            self.area.body.columnconfigure(col, weight=1 if col < self.columns else 0, minsize=0,
                                           uniform='emoji' if col < self.columns else '')
        pages = max(1, math.ceil(len(self.matches)/self.page_size))
        self.page_label.configure(text=f'{self.page+1} / {pages}')
        self.previous.configure(state='normal' if self.page else 'disabled')
        self.next.configure(state='normal' if self.page+1 < pages else 'disabled')
        self.status.configure(text=f'{len(self.matches)} 个表情 · 中文 / 英文 / 表情搜索')
        if not self.matches:
            ttk.Label(self.area.body, text='没有匹配的表情，试试“火箭”“文件”或 rocket。',
                      wraplength=440, style='Subheader.TLabel').grid(row=0, column=0, columnspan=self.columns, pady=24)
        rows = self.matches[self.page*self.page_size:(self.page+1)*self.page_size]
        for index, row in enumerate(rows):
            cell = ttk.Frame(self.area.body, width=60, height=58)
            cell.grid(row=index//self.columns, column=index%self.columns, padx=3, pady=3, sticky='nsew')
            cell.grid_propagate(False)
            cell.columnconfigure(0, weight=1)
            cell.rowconfigure(0, weight=1)
            button = ttk.Button(cell, text=row['emoji'], style='EmojiPicker.TButton',
                                command=lambda value=row['emoji']: self.choose(value))
            button.grid(row=0, column=0, sticky='nsew')
            Tooltip(button, f"{row['emoji']}  {row['label']} · {row['category']}")
            self.buttons.append(button)
            def show(png, error, button=button):
                if self.closed or not button.winfo_exists() or error:
                    return
                photo = tk.PhotoImage(master=self, data=png)
                self.images.append(photo)
                button.configure(image=photo, text='')
            self.owner.preview_service.request(self.prefix+str(index), row['emoji'], 32, show)
        self.area.canvas.yview_moveto(0)

    def destroy(self):
        if self.closed:
            return
        self.closed = True
        self.owner.preview_service.cancel(self.prefix)
        for job in (self.search_job, self.resize_job):
            if job is not None:
                self.after_cancel(job)
        self.chrome.detach()
        super().destroy()
