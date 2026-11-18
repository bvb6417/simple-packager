from __future__ import annotations

import ast
from dataclasses import dataclass
from importlib import metadata
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
import tokenize
from native_icon import render_text_icon
from pathlib import Path
from urllib.parse import urlparse

from system_python_launcher import PROJECT_SETTINGS_DIRECTORY

APP_NAME = "UV Python 精简打包工具"
APP_VERSION = "2.7.0"
DEFAULT_PYINSTALLER_VERSION = "6.21.0"
LEGACY_SYSTEM_PYTHON_PACKAGE_MODE = "系统 Python 启动器（单文件，不内置环境）"
SYSTEM_PYTHON_PACKAGE_MODE = "系统 Python 启动器（完整项目，内置资源）"
SYSTEM_PYTHON_SOURCE_ONLY_MODE = "系统 Python 启动器（仅源码，资源外置）"
SYSTEM_PYTHON_ENTRY_ONLY_MODE = "系统 Python 启动器（入口包装）"
PACKAGE_ICON_PNG = "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"
SKIP_DIRS = {
    PROJECT_SETTINGS_DIRECTORY,
    ".git",
    ".idea",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tmp",
    ".tox",
    ".uv-packager",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "env",
    "node_modules",
    "venv",
}
ENTRY_PRIORITIES = {
    "main.py": 0,
    "app.py": 1,
    "run.py": 2,
    "gui.py": 3,
    "cli.py": 4,
    "server.py": 5,
    "start.py": 6,
}
COMMON_DEV_EXCLUDES = (
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "setuptools",
    "sphinx",
    "wheel",
)
AUTO_COLLECT_DATA_PACKAGES = {
    "ttkbootstrap": "ttkbootstrap",
}
EMOJI_LIBRARY = {
    "系统与导航": [
        "🏠", "⚙️", "🔍", "🧭", "📌", "🔙", "🔝", "🔄", "➕", "➖",
        "❌", "✅", "ℹ️", "🌐", "🍔", "🚪", "🔑", "🔒", "🔓", "🛑",
        "⚠️", "🚫", "❓", "❗", "⬆️", "⬇️", "⬅️", "➡️", "🔃", "🔁",
    ],
    "文件与编辑": [
        "📦", "📁", "📂", "📄", "📑", "📝", "✏️", "✒️", "💾", "📋",
        "✂️",
        "📎", "🖇️", "🗑️", "📥", "📤", "🖨️", "🖍️", "🖌️", "📏", "📐",
        "🗂️", "🗃️", "🗄️", "🧾", "📖", "📕", "📗", "📘", "📙", "📚",
    ],
    "媒体与通信": [
        "🎵", "🎶", "🎧", "🎤", "🎥", "🎬", "📺", "📷", "📸", "🖼️",
        "💬", "🗨️", "💭", "✉️", "📧", "📨", "📞", "☎️", "🔔", "🔕",
        "📣", "📢", "🎙️", "📻", "▶️", "⏸️", "⏹️", "⏺️", "⏭️", "⏮️",
    ],
    "用户与社交": [
        "👤", "👥", "🧑", "👨", "👩", "🤝", "👍", "👎", "👏", "🙌",
        "🌟", "⭐", "❤️", "🏆", "🎖️", "👑", "🛡️", "👁️", "👣", "🖐️",
        "🎁", "🎉", "🎈", "🎂", "🎓", "💼", "👔", "👗", "💍", "💎",
    ],
    "工具与开发": [
        "🛠️", "🔧", "🔨", "⛏️", "🔩", "🧲", "🧪", "🧫", "🧬", "🔬",
        "🔭", "📡", "💻", "🖥️", "⌨️", "🖱️", "🖲️", "🔋", "🔌", "💡",
        "🔦", "📊", "📈", "📉", "📅", "📆", "🕰️", "⏰", "⏱️", "🚀",
    ],
    "笑脸与情感": [
        "😀", "😁", "😂", "🤣", "😅", "😊", "😇", "🙂", "🙃", "😉",
        "😌", "😍", "🥰", "😘", "😗", "😋", "😛", "😝", "😜", "🤪",
        "🤨", "🧐", "🤓", "😎", "🤩", "🥳", "😏", "😒", "😞", "😔",
        "😟", "😕", "🙁", "😣", "😖", "😫", "😩", "🥺", "😢", "😭",
        "😤", "😠", "😡", "🤬", "🤯", "😳", "🥵", "🥶", "😱", "😨",
        "🤗", "🤔", "🤭", "🤫", "🤥", "😶", "😐", "😑", "😬", "🙄",
        "😴", "🤤", "😵", "🤐", "🥴", "🤢", "🤮", "🤧", "😷", "🤡",
    ],
    "手势与人物": [
        "👋", "🤚", "🖐", "✋", "🖖", "👌", "🤌", "🤏", "✌️", "🤞",
        "🤟", "🤘", "🤙", "👈", "👉", "👆", "🖕", "👇", "☝️", "👍",
        "👎", "✊", "👊", "🤛", "🤜", "👏", "🙌", "👐", "🤲", "🤝",
        "🙏", "✍️", "💅", "🤳", "💪", "🦵", "🦶", "👂", "🦻", "👃",
        "🧠", "🫀", "🫁", "🦷", "骨", "👀", "👁", "👅", "👄", "💋",
    ],
    "动物与自然": [
        "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯",
        "🦁", "🐮", "🐷", "🐸", "🐵", "🐔", "🐧", "🐦", "🐤", "🦆",
        "🦅", "🦉", "🦇", "🐺", "🐗", "🐴", "🦄", "🐝", "🪱", "🐛",
        "🦋", "🐌", "🐞", "🐜", "🪰", "🪲", "🪳", "🦟", "🦗", "🕷",
        "🌸", "💮", "🏵", "🌹", "🥀", "🌺", "🌻", "🌼", "🌷", "🌱",
        "🌲", "🌳", "🌴", "🌵", "🌾", "🌿", "🍀", "🍁", "🍂", "🍃",
        "🔥", "☀️", "🌤", "⛅", "🌥", "☁️", "🌦", "🌧", "⛈", "🌩",
        "🌨", "❄️", "☃️", "⛄", "🌬", "💨", "🌪", "🌫", "🌈", "☔",
    ],
    "食物与饮料": [
        "🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐",
        "🍈", "🍒", "🍑", "🥭", "🍍", "🥥", "🥝", "🍅", "🍆", "🥑",
        "🥦", "🥬", "🥒", "🌶", "🫑", "🌽", "🥕", "🫒", "🧄", "🧅",
        "🍞", "🥐", "🥖", "🫓", "🥨", "🥯", "🥞", "🧇", "🧀", "🍖",
        "🍗", "🥩", "🥓", "🍔", "🍟", "🍕", "🌭", "🥪", "🌮", "🌯",
        "☕", "🫖", "🍵", "🥤", "🧋", "🧃", "🧉", "🥛", "🍺", "🍻",
    ],
    "符号与物品": [
        "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔",
        "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💟", "☮️",
        "✝️", "☪️", "🕉", "☸️", "✡️", "🔯", "🕎", "☯️", "☦️", "🛐",
        "💯", "💢", "💬", "👁️‍🗨️", "🗨️", "🗯️", "💭", "💤", "💮", "♨️",
        "✅", "❌", "❓", "❗", "⚠️", "⛔", "🚫", "☢️", "☣️", "⬆️",
        "⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🥏", "🎱",
        "🎮", "🕹️", "🎰", "🎲", "🧩", "🧸", "🪀", "🪁", "🔮", "🪄",
        "📱", "💻", "⌚", "💡", "🔦", "🕯️", "📚", "🎉", "✨", "🎁",
    ],
}
INDEX_URLS = (
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://mirrors.aliyun.com/pypi/simple",
    "https://mirrors.cloud.tencent.com/pypi/simple",
    "https://pypi.org/simple",
)
DOMESTIC_INDEX_HOSTS = {
    "mirrors.aliyun.com",
    "mirrors.cloud.tencent.com",
    "pypi.tuna.tsinghua.edu.cn",
}


@dataclass(frozen=True)
class SystemLauncherSettings:
    project: Path
    entry: Path
    name: str
    dist: Path
    output: Path
    console: bool
    icon: Path | None
    source_only: bool
    entry_only: bool = False
IMPORT_NAME_OVERRIDES = {
    "PIL": "Pillow",
    "OpenGL": "PyOpenGL",
    "bs4": "beautifulsoup4",
    "cv2": "opencv-python",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "fitz": "PyMuPDF",
    "jwt": "PyJWT",
    "serial": "pyserial",
    "sklearn": "scikit-learn",
    "win32api": "pywin32",
    "win32com": "pywin32",
    "yaml": "PyYAML",
    "Crypto": "pycryptodome",
    "Cryptodome": "pycryptodomex",
    "websocket": "websocket-client",
    "docx": "python-docx",
    "pptx": "python-pptx",
}
IMPORT_ERROR_NAMES = {"ImportError", "ModuleNotFoundError"}
PYTHON_SOURCE_SUFFIXES = {".py", ".pyw", ".pyd"}
PYTHON_CODE_SUFFIXES = {".py", ".pyw", ".pyc", ".pyo", ".pyd"}
DEFAULT_REQUIREMENTS_NAME = "runtime-requirements.txt"
FAST_DEPENDENCY_MODE = "本地快速扫描 imports（不锁版本，推荐）"
LOCKED_DEPENDENCY_MODE = "本地扫描 imports 并锁定版本（较慢）"
GENERATED_REQUIREMENTS_MARKER = "# 由 py简洁打包 本地扫描生成"


def creation_flags() -> int:
    if os.name != "nt":
        return 0
    return subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP


def locate_uv() -> Path | None:
    executable = shutil.which("uv")
    if executable:
        return Path(executable)

    candidates = [
        Path.home() / ".local" / "bin" / "uv.exe",
        Path.home() / ".cargo" / "bin" / "uv.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "uv" / "uv.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def uv_cache_directory(uv: Path | None, cwd: Path | None = None) -> Path | None:
    """Report uv's effective cache location for this working directory."""
    if uv is None:
        return None
    try:
        result = subprocess.run(
            [str(uv), "cache", "dir"], cwd=cwd, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=5,
            creationflags=creation_flags(),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    return None


def split_names(value: str) -> list[str]:
    normalized = value.replace("，", ",").replace("\n", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def requirement_names(path: Path | None) -> set[str]:
    if path is None:
        return set()
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        return set()

    names: set[str] = set()
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith(("#", "-", "git+", "http://", "https://")):
            continue
        match = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if match:
            names.add(re.sub(r"[-_.]+", "-", match.group(1)).casefold())
    return names


def is_network_failure(output: str) -> bool:
    normalized = output.casefold()
    markers = (
        "certificate",
        "client error (connect)",
        "connection reset",
        "dns",
        "failed to fetch",
        "network",
        "proxy",
        "request failed",
        "timed out",
        "timeout",
        "tls",
        "unexpected eof",
    )
    return any(marker in normalized for marker in markers)


def domestic_index_host(index_url: str) -> str | None:
    host = (urlparse(index_url).hostname or "").casefold()
    return host if host in DOMESTIC_INDEX_HOSTS else None


def add_no_proxy_host(env: dict[str, str], host: str) -> None:
    entries: list[str] = []
    for key in ("NO_PROXY", "no_proxy"):
        for entry in env.get(key, "").split(","):
            normalized = entry.strip()
            if normalized and normalized not in entries:
                entries.append(normalized)
    if host not in entries:
        entries.append(host)
    value = ",".join(entries)
    env["NO_PROXY"] = value
    env["no_proxy"] = value


def _module_file_paths(stem: Path) -> list[Path]:
    paths: list[Path] = []
    source_file = stem.with_suffix(".py")
    if source_file.is_file():
        paths.append(source_file.resolve())

    extension_files = [
        stem.with_suffix(".pyd"),
        stem.with_name(f"{stem.name}_d.pyd"),
    ]
    extension_files.extend(stem.parent.glob(f"{stem.name}.*.pyd"))
    for extension_file in extension_files:
        if extension_file.is_file():
            paths.append(extension_file.resolve())
    return list(dict.fromkeys(paths))


def _local_module_paths(base: Path, module: str) -> list[Path]:
    parts = [part for part in module.split(".") if part]
    if not parts:
        return []
    paths: list[Path] = []
    current = base
    for part in parts:
        current /= part
        paths.extend(_module_file_paths(current / "__init__"))
    paths.extend(_module_file_paths(base.joinpath(*parts)))
    return list(dict.fromkeys(paths))


def _resolve_local_module(
    roots: list[Path],
    module: str,
) -> tuple[Path | None, list[Path]]:
    """Return the first search root that provides ``module`` and its files."""
    for root in roots:
        paths = _local_module_paths(root, module)
        if paths:
            return root, paths
    return None, []


def _in_skipped_directory(path: Path, project: Path) -> bool:
    try:
        parts = path.relative_to(project).parts
    except ValueError:
        return True
    return any(part in SKIP_DIRS for part in parts)


def _string_constants(
    node: ast.AST | None,
    assignments: dict[str, ast.AST],
    depth: int = 0,
) -> list[str]:
    """String literals inside a path expression, following simple module-level names."""
    if node is None or depth > 3:
        return []
    values: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            values.append(child.value)
        elif isinstance(child, ast.Name) and child.id in assignments:
            values.extend(
                _string_constants(assignments[child.id], assignments, depth + 1)
            )
    return values


def _sys_path_roots(tree: ast.Module, path: Path, project: Path) -> list[Path]:
    """Project folders a script puts on sys.path, e.g. ``sys.path.insert(0, BASE / "src")``."""
    assignments: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            assignments[node.target.id] = node.value

    roots: list[Path] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.args
        ):
            continue
        function = node.func
        owner = function.value
        sys_path_call = (
            function.attr in ("insert", "append")
            and isinstance(owner, ast.Attribute)
            and owner.attr == "path"
            and isinstance(owner.value, ast.Name)
            and owner.value.id == "sys"
        )
        site_call = (
            function.attr == "addsitedir"
            and isinstance(owner, ast.Name)
            and owner.id == "site"
        )
        if not (sys_path_call or site_call):
            continue
        for value in _string_constants(node.args[-1], assignments):
            text = value.strip().strip("/\\")
            if not text or text in (".", "..") or len(text) > 200:
                continue
            for base in (path.parent, project):
                try:
                    candidate = (base / text).resolve()
                except (OSError, ValueError):
                    continue
                if (
                    candidate != project
                    and candidate.is_dir()
                    and not _in_skipped_directory(candidate, project)
                ):
                    roots.append(candidate)
                    break
    return list(dict.fromkeys(roots))


def _fallback_import_nodes(tree: ast.Module) -> set[int]:
    """Imports inside ``except ImportError`` handlers are optional fallbacks."""

    def catches_import_error(handler_type: ast.AST | None) -> bool:
        if handler_type is None:
            return False
        names = handler_type.elts if isinstance(handler_type, ast.Tuple) else [handler_type]
        return any(
            (isinstance(name, ast.Name) and name.id in IMPORT_ERROR_NAMES)
            or (isinstance(name, ast.Attribute) and name.attr in IMPORT_ERROR_NAMES)
            for name in names
        )

    nodes: set[int] = set()
    for node in ast.walk(tree):
        for handler in getattr(node, "handlers", ()):
            if isinstance(handler, ast.ExceptHandler) and catches_import_error(handler.type):
                for statement in handler.body:
                    for child in ast.walk(statement):
                        if isinstance(child, (ast.Import, ast.ImportFrom)):
                            nodes.add(id(child))
    return nodes


@dataclass
class ImportScan:
    python_files: list[Path]
    imported_modules: set[str]
    unreadable: list[str]
    source_roots: list[Path]


def scan_imports(project: Path, entry: Path) -> ImportScan:
    """Follow local imports from the entry and collect third-party imports.

    Local modules are searched beside the entry, in folders the scanned code
    adds to ``sys.path`` (for example ``src``), in the project root and in a
    conventional ``src`` folder. ``source_roots`` lists the extra folders that
    actually provided modules; PyInstaller needs them as ``--paths``.
    """
    project = project.resolve()
    entry = entry.resolve()
    pending = [entry]
    python_files: list[Path] = []
    seen: set[Path] = set()
    imported_modules: set[str] = set()
    unreadable: list[str] = []
    added_roots: list[Path] = []
    used_roots: list[Path] = []
    conventional = project / "src"

    def import_roots() -> list[Path]:
        roots = [entry.parent, *added_roots, project]
        if conventional.is_dir():
            roots.append(conventional)
        return list(dict.fromkeys(roots))

    def queue_local(paths: list[Path]) -> bool:
        local = False
        for candidate in paths:
            try:
                candidate.relative_to(project)
            except ValueError:
                continue
            local = True
            if (
                candidate.suffix.casefold() in {".py", ".pyw"}
                and candidate not in seen
                and candidate not in pending
            ):
                pending.append(candidate)
        return local

    def resolve_absolute(module: str) -> bool:
        root, paths = _resolve_local_module(import_roots(), module)
        local = queue_local(paths)
        if local and root is not None and root not in (entry.parent, project):
            used_roots.append(root)
        return local

    while pending:
        path = pending.pop(0)
        if path in seen:
            continue
        seen.add(path)
        python_files.append(path)
        try:
            with tokenize.open(path) as stream:
                source = stream.read()
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError, UnicodeError):
            unreadable.append(str(path.relative_to(project)))
            continue
        for root in _sys_path_roots(tree, path, project):
            if root not in added_roots:
                added_roots.append(root)
        optional = _fallback_import_nodes(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not resolve_absolute(alias.name) and id(node) not in optional:
                        imported_modules.add(alias.name.split(".", 1)[0])
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    base = path.parent
                    for _ in range(node.level - 1):
                        base = base.parent
                    try:
                        base.relative_to(project)
                    except ValueError:
                        continue
                    queue_local(_local_module_paths(base, module))
                    for alias in node.names:
                        if alias.name != "*":
                            child = ".".join(
                                part for part in (module, alias.name) if part
                            )
                            queue_local(_local_module_paths(base, child))
                elif module:
                    local = resolve_absolute(module)
                    for alias in node.names:
                        if alias.name != "*":
                            local = resolve_absolute(f"{module}.{alias.name}") or local
                    if not local and id(node) not in optional:
                        imported_modules.add(module.split(".", 1)[0])

    return ImportScan(
        python_files,
        imported_modules,
        unreadable,
        list(dict.fromkeys(used_roots)),
    )


def private_tk_resources(project: Path) -> list[tuple[Path, str]]:
    """Keep a project-local Windows Tcl/Tk 8.6 distribution at its runtime paths."""
    runtime = project / "runtime"
    dlls = [runtime / "bin" / name for name in ("tcl86t.dll", "tk86t.dll")]
    libraries = runtime / "lib"
    markers = [libraries / "tcl8.6" / "init.tcl", libraries / "tk8.6" / "tk.tcl"]
    if not all(path.is_file() for path in (*dlls, *markers)):
        return []

    resources = [(dll, "runtime/bin") for dll in dlls]
    for name in ("tcl8", "tcl8.6", "tk8.6", "dde1.4", "reg1.3"):
        folder = libraries / name
        if folder.is_dir():
            resources.append((folder, folder.relative_to(project).as_posix()))
    resources.extend((path, "runtime") for path in sorted(runtime.glob("LICENSE*.txt")) if path.is_file())
    return resources


def source_root_data(root: Path, project: Path) -> list[tuple[Path, str]]:
    """Resource files in an extra source root, mapped to the bundle root.

    PyInstaller places modules found through ``--paths <root>`` at the top of
    the bundle, so ``Path(__file__).parent / "themes"`` only keeps working if
    the root's resources land there too.
    """
    data: list[tuple[Path, str]] = []

    def has_python(folder: Path) -> bool:
        return any(
            item.suffix.casefold() in PYTHON_SOURCE_SUFFIXES
            for item in folder.rglob("*")
            if item.is_file() and not _in_skipped_directory(item, project)
        )

    def add_files(folder: Path) -> None:
        for item in sorted(folder.rglob("*")):
            if (
                item.is_file()
                and item.suffix.casefold() not in PYTHON_CODE_SUFFIXES
                and not _in_skipped_directory(item, project)
            ):
                destination = item.parent.relative_to(root).as_posix()
                data.append((item, destination or "."))

    for item in sorted(root.iterdir()):
        if item.name in SKIP_DIRS or item.name.startswith("."):
            continue
        if item.is_file():
            if item.suffix.casefold() not in PYTHON_CODE_SUFFIXES:
                data.append((item, "."))
        elif item.is_dir():
            if has_python(item):
                add_files(item)
            else:
                data.append((item, item.name))
    return data


def is_generated_requirements(path: Path) -> bool:
    try:
        with path.open(encoding="utf-8-sig") as stream:
            first_line = stream.readline()
    except (OSError, UnicodeError):
        return False
    return first_line.startswith(GENERATED_REQUIREMENTS_MARKER)


def dependency_output_path(project: Path, selected: str) -> tuple[Path, bool]:
    """Where a dependency scan may write; a hand-written file is never overwritten.

    Returns the target path and whether it was redirected away from ``selected``.
    """
    default = (project / DEFAULT_REQUIREMENTS_NAME).resolve()
    path = Path(selected).expanduser() if selected else default
    if not path.is_absolute():
        path = project / path
    path = path.resolve()
    if path.is_file() and not is_generated_requirements(path):
        for candidate in (default, project / 'runtime-requirements.generated.txt'):
            if not candidate.exists() or is_generated_requirements(candidate):
                return candidate.resolve(), True
        raise ValueError('依赖输出文件均为手写文件，请指定一个新的输出路径。')
    return path, False



def scan_local_requirements(
    project: Path,
    entry: Path,
    output_path: Path,
) -> tuple[int, list[str]]:
    scan = scan_imports(project, entry)

    standard_library = set(getattr(sys, "stdlib_module_names", ()))
    standard_library.update(sys.builtin_module_names)
    third_party = {
        name
        for name in scan.imported_modules
        if name
        and name != "__future__"
        and name not in standard_library
        and not name.startswith("_")
    }

    try:
        installed_mapping = metadata.packages_distributions()
    except Exception:
        installed_mapping = {}

    distributions: set[str] = set()
    for import_name in third_party:
        distribution = IMPORT_NAME_OVERRIDES.get(import_name)
        if distribution is None:
            installed = installed_mapping.get(import_name) or []
            distribution = installed[0] if installed else import_name
        distributions.add(distribution)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [GENERATED_REQUIREMENTS_MARKER, *sorted(distributions, key=str.casefold)]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(scan.python_files), scan.unreadable



def application_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    if hasattr(sys, "_MEIPASS") and (launcher_dir := os.environ.get("SYSTEM_PYTHON_LAUNCHER_DIR")):
        return Path(launcher_dir).resolve()
    return Path(__file__).resolve().parent


APP_DIR = application_directory()
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def project_settings_path(app_dir: Path, project: Path) -> Path:
    project = project.resolve()
    key = os.path.normcase(str(project))
    digest = hashlib.sha256(os.fsencode(key)).hexdigest()[:20]
    label = re.sub(r'[<>:"/\\|?*]', "_", os.path.normcase(project.name))
    label = label[:36].rstrip(" .") or "project"
    return app_dir / PROJECT_SETTINGS_DIRECTORY / f"{label}-{digest}.json"


def validate_output_name(name: str) -> str:
    if not name or name in {'.', '..'} or name.endswith((' ', '.')):
        raise ValueError('程序名称不能为空，也不能以空格或句点结尾。')
    if any(c in '<>:"/\\|?*' or ord(c) < 32 for c in name):
        raise ValueError('程序名称包含 Windows 文件名不允许的字符。')
    stem = name.split('.', 1)[0].upper()
    if stem in {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$'} or re.fullmatch(r'(COM|LPT)[1-9¹²³]', stem):
        raise ValueError('程序名称不能使用 Windows 保留名称。')
    return name


class PackagerController:
    """Shared planning, settings and task execution; no Tk interpreter required."""
    def _apply_project_defaults(self, project: Path) -> None:
        default_requirements = project / DEFAULT_REQUIREMENTS_NAME
        existing = next(
            (
                path
                for path in (
                    default_requirements,
                    project / "requirements.txt",
                    project / "requirements.lock",
                )
                if path.is_file()
            ),
            None,
        )
        self.requirements_var.set(str(existing or default_requirements))
        self.dist_var.set(str(project / "dist"))


    def _entry_path(self, project: Path) -> Path | None:
        value = self.entry_var.get().strip().strip('"')
        if not value:
            self.dialogs.showwarning(APP_NAME, "请选择入口文件。")
            return None
        path = Path(value)
        if not path.is_absolute():
            path = project / path
        path = path.resolve()
        if not path.is_file():
            self.dialogs.showerror(APP_NAME, f"入口文件不存在：\n{path}")
            return None
        if path.suffix.lower() not in {'.py', '.pyw'} or not path.is_relative_to(project):
            self.dialogs.showerror(APP_NAME, '入口必须是项目目录内的 .py 或 .pyw 文件。')
            return None
        return path


    def _requirements_path(self, project: Path) -> Path | None:
        value = self.requirements_var.get().strip().strip('"')
        return (project / Path(value).expanduser()).resolve() if value else None


    def _output_details(self, project: Path) -> tuple[str, Path] | None:
        name = self.output_name_var.get()
        if not name:
            self.dialogs.showwarning(APP_NAME, "请输入程序名称。")
            return None
        try:
            validate_output_name(name)
        except ValueError as exc:
            self.dialogs.showerror(APP_NAME, str(exc))
            return None

        value = self.dist_var.get().strip().strip('"')
        dist = project / (Path(value).expanduser() if value else "dist")
        return name, dist.resolve()


    def _select_icon(self, project: Path, generated_icon: Path) -> Path | None:
        filename, text = self._icon_values()
        if text:
            try:
                self._render_icon(text, generated_icon)
            except (OSError, RuntimeError, ValueError) as exc:
                raise ValueError(f"无法生成图标文本：\n{exc}") from exc
            return generated_icon
        if not filename:
            return None
        icon = project / Path(filename).expanduser()
        if not icon.is_file():
            raise ValueError(f"图标文件不存在：\n{icon}")
        return icon.resolve()


    def _system_launcher_settings(self) -> SystemLauncherSettings | None:
        if os.name != "nt":
            self.dialogs.showerror(APP_NAME, "系统 Python 启动器目前仅支持 Windows。")
            return None
        project = self._project_path(required=True)
        if project is None:
            return None
        entry = self._entry_path(project)
        if entry is None:
            return None
        details = self._output_details(project)
        if details is None:
            return None
        name, dist = details
        output_name = name if name.casefold().endswith(".exe") else f"{name}.exe"
        output = dist / output_name
        launcher_title = name[:-4] if name.casefold().endswith(".exe") else name

        try:
            icon = self._select_icon(project, project / ".tmp" / "uv-packager" / "generated-system-launcher-icon.ico")
        except ValueError as exc:
            self.dialogs.showerror(APP_NAME, str(exc))
            return None

        mode = self.package_mode_var.get().strip()
        return SystemLauncherSettings(
            project=project,
            entry=entry,
            name=launcher_title,
            dist=dist,
            output=output,
            console=not self.window_mode_var.get().startswith("不显示"),
            icon=icon,
            source_only=mode in {SYSTEM_PYTHON_SOURCE_ONLY_MODE, SYSTEM_PYTHON_ENTRY_ONLY_MODE},
            entry_only=mode == SYSTEM_PYTHON_ENTRY_ONLY_MODE,
        )


    def _is_system_python_mode(self) -> bool:
        return self.package_mode_var.get().strip().startswith("系统 Python 启动器")


    def _build_command(self) -> tuple[list[str], Path, Path] | None:
        if self._is_system_python_mode():
            self.dialogs.showerror(
                APP_NAME,
                "系统 Python 启动器不能进入 PyInstaller 构建流程。",
            )
            return None
        project = self._project_path(required=True)
        if project is None:
            return None
        entry = self._entry_path(project)
        if entry is None:
            return None
        details = self._output_details(project)
        if details is None:
            return None
        name, dist = details
        requirements = self._requirements_path(project)
        if requirements is not None and not requirements.is_file():
            if not self.dialogs.askyesno(
                APP_NAME,
                f"依赖文件尚不存在：\n{requirements}\n\n"
                "是否按“无第三方依赖”继续？\n"
                "如项目使用第三方库，建议先取消并生成依赖。",
            ):
                return None
            requirements = None

        requested = self.pyinstaller_version_var.get().strip()
        pin = "" if requested in {"", "自动"} else requested
        python = self.python_version_var.get().strip()
        executable = Path(sys.executable)
        if executable.name.lower() == "pythonw.exe" and executable.with_name("python.exe").is_file():
            executable = executable.with_name("python.exe")
        if not self._ensure_uv():
            return None
        command = [str(self.uv_path), "tool", "run", "--isolated"]
        if python and not python.startswith("系统默认"):
            command.extend(["--python", python])
        elif not getattr(sys, "frozen", False):
            command.extend(["--python", str(executable)])
        version = pin or DEFAULT_PYINSTALLER_VERSION
        command.extend(["--from", f"pyinstaller=={version}"])
        if requirements is not None:
            command.extend(["--with-requirements", str(requirements)])
        command.append("pyinstaller")
        self.build_environment = f"uv 隔离环境 · PyInstaller {version}"
        command.append("--noconfirm")
        if self.clean_var.get():
            command.append("--clean")
        command.append(
            "--onefile" if self.package_mode_var.get().startswith("单文件") else "--onedir"
        )
        command.append(
            "--windowed"
            if self.window_mode_var.get().startswith("不显示")
            else "--console"
        )

        work_root = project / ".uv-packager"
        command.extend(
            [
                "--name",
                name,
                "--distpath",
                str(dist),
                "--workpath",
                str(work_root / "build"),
                "--specpath",
                str(work_root),
                "--paths",
                str(project),
            ]
        )
        # Folders such as src/ that the entry puts on sys.path at runtime are
        # invisible to PyInstaller unless they are passed explicitly.
        try:
            source_roots = scan_imports(project, entry).source_roots
        except (OSError, ValueError):
            source_roots = []
        for root in source_roots:
            command.extend(["--paths", str(root)])
            if self.auto_collect_data_var.get():
                for source, destination in source_root_data(root, project):
                    command.extend(["--add-data", f"{source}{os.pathsep}{destination}"])
        try:
            icon = self._select_icon(project, work_root / "generated-icon.ico")
        except ValueError as exc:
            self.dialogs.showerror(APP_NAME, str(exc))
            return None
        if icon is not None:
            command.extend(["--icon", str(icon.resolve())])

        preset = self.preset_var.get()
        exclude_dev = self.exclude_dev_var.get() or preset.startswith("精简优先")
        if preset.startswith("兼容优先"):
            command.append("--noupx")
        elif preset.startswith("导入调试"):
            command.append("--debug=imports")
        for module in split_names(self.hidden_imports_var.get()):
            command.extend(["--hidden-import", module])
        if self.auto_collect_data_var.get():
            for source, destination in private_tk_resources(project):
                command.extend(["--add-data", f"{source}{os.pathsep}{destination}"])
            installed_names = requirement_names(requirements)
            for distribution_name, import_name in AUTO_COLLECT_DATA_PACKAGES.items():
                if distribution_name in installed_names:
                    command.extend(["--collect-data", import_name])
        excludes = split_names(self.excludes_var.get())
        if exclude_dev:
            excludes.extend(COMMON_DEV_EXCLUDES)
        for module in dict.fromkeys(excludes):
            command.extend(["--exclude-module", module])
        for line in self.extra_args_text.get("1.0", "end").splitlines():
            argument = line.strip()
            if argument and not argument.startswith("#"):
                option = argument.split('=', 1)[0].split(' ', 1)[0]
                if option in {'--distpath', '--workpath', '--specpath', '--name', '-n', '--onefile', '-F', '--onedir', '-D'}:
                    self.dialogs.showerror(APP_NAME, f'附加参数 {option} 会覆盖受管理的输出路径或模式，请使用界面/CLI 对应选项。')
                    return None
                command.append(argument)
        command.append(str(entry))
        return command, project, dist


    def _delete_build_work_cache(
        self,
        project: Path,
        *,
        system_launcher: bool,
        protected_path: Path,
    ) -> str | None:
        project = project.resolve()
        relative = (
            Path(".tmp") / "uv-packager"
            if system_launcher
            else Path(".uv-packager")
        )
        cache_path = project / relative
        try:
            expected_parent = cache_path.parent.resolve()
            expected_parent.relative_to(project)
            resolved_cache = cache_path.resolve()
            if resolved_cache != expected_parent / cache_path.name:
                raise OSError("缓存目录是指向其他位置的链接")
            protected = protected_path.resolve()
            try:
                protected.relative_to(resolved_cache)
            except ValueError:
                pass
            else:
                raise OSError("输出目录位于缓存目录内，为防止删除结果已取消清理")
            if not resolved_cache.exists():
                self.append_log(f"工作缓存不存在，无需删除：{cache_path}")
                return None
            if not resolved_cache.is_dir():
                raise OSError("缓存路径不是文件夹")
            shutil.rmtree(resolved_cache)
            self.append_log(f"已删除工作缓存：{cache_path}")
            return None
        except (OSError, RuntimeError, ValueError) as exc:
            message = f"工作缓存未能删除：{exc}"
            self.append_log(message)
            return message


    def _run_callable_task(self, title: str, operation, on_success=None) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            self.dialogs.showwarning(APP_NAME, "已有任务正在运行，请先等待或停止它。")
            return
        self.cancel_requested = False
        self.task_success_callback = on_success
        self._set_busy(True, title)
        self._task_started(title)
        self.append_log("=" * 72)
        self.append_log(f"开始：{title}")

        def worker() -> None:
            try:
                operation()
                if self.cancel_requested:
                    raise InterruptedError("任务已取消")
                self.task_queue.put(("done", True, f"{title}完成"))
            except InterruptedError as exc:
                self.task_queue.put(("done", False, str(exc), "cancelled"))
            except Exception as exc:
                self.task_queue.put(("done", False, str(exc), "error"))

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()


    def _offline_tool_environment(self, command, cwd, env, indexes):
        """Find an offline uv configuration before starting the actual build."""
        probe = [*command[:command.index("--noconfirm")], "--version"]
        # Preserve single-index cache hits, then try each mirror as the first
        # source in the combined search. A cached listing from an earlier
        # mirror can otherwise mask the required version on a later mirror.
        configs = [({"UV_DEFAULT_INDEX": index}, False) for index in indexes]
        if len(indexes) > 1:
            for first in range(len(indexes)):
                ordered = indexes[first:] + indexes[:first]
                extras = " ".join((*ordered[:-1], env.get("UV_INDEX", ""))).strip()
                configs.append(({"UV_DEFAULT_INDEX": ordered[-1], "UV_INDEX": extras}, True))

        for config, uses_multiple_indexes in configs:
            if self.cancel_requested:
                raise InterruptedError("任务已取消")
            settings = dict(env, UV_OFFLINE="1", **config)
            self.running_process = subprocess.Popen(
                probe, cwd=cwd, env=settings, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=creation_flags(),
            )
            if self.cancel_requested:
                self.cancel_task()
            status = self.running_process.wait()
            self.running_process = None
            if self.cancel_requested:
                raise InterruptedError("任务已取消")
            if status == 0:
                return settings, uses_multiple_indexes
        return None, False

    def _run_task(
        self,
        title: str,
        steps: list[tuple[str, list[str], Path]],
        on_success=None,
    ) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            self.dialogs.showwarning(APP_NAME, "已有任务正在运行，请先等待或停止它。")
            return
        self.cancel_requested = False
        self.task_success_callback = on_success
        self._set_busy(True, title)
        self._task_started(title)
        self.append_log("=" * 72)
        self.append_log(f"开始：{title}")

        def worker() -> None:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            env["UV_NO_PROGRESS"] = "1"
            env["UV_NATIVE_TLS"] = "1"
            try:
                active_indexes = list(INDEX_URLS)
                for label, command, cwd in steps:
                    if self.cancel_requested:
                        raise InterruptedError("任务已取消")
                    self.task_queue.put(("log", f"\n[{label}]"))
                    self.task_queue.put(("log", self._format_command(command)))
                    invokes_uv = self.uv_path and command[0] == str(self.uv_path)
                    if invokes_uv and (cache := uv_cache_directory(self.uv_path, cwd)) is not None:
                        self.task_queue.put(("log", f"uv 缓存目录：{cache}"))
                    attempt_indexes = active_indexes.copy() if invokes_uv else []
                    attempt_indexes = attempt_indexes or [""]
                    offline_env = None
                    if command[1:3] == ["tool", "run"] and "--noconfirm" in command:
                        isolated_env = env.copy()
                        isolated_env.pop("PYTHONPATH", None)
                        isolated_env.pop("PYTHONHOME", None)
                        isolated_env["PYTHONNOUSERSITE"] = "1"
                        offline_env, mixed_indexes = self._offline_tool_environment(
                            command, cwd, isolated_env, attempt_indexes
                        )
                        if offline_env is not None:
                            attempt_indexes = [offline_env["UV_DEFAULT_INDEX"]]
                            kind = "跨镜像缓存" if mixed_indexes else "uv 缓存"
                            self.task_queue.put(("log", f"{kind}命中，离线执行 PyInstaller"))
                        else:
                            self.task_queue.put(("log", "离线缓存不足，uv 将从下载源补齐依赖"))
                    else:
                        isolated_env = env
                    for attempt, current_index in enumerate(attempt_indexes, start=1):
                        attempt_env = (offline_env or isolated_env).copy()
                        if current_index:
                            attempt_env["UV_DEFAULT_INDEX"] = current_index
                        else:
                            attempt_env.pop("UV_DEFAULT_INDEX", None)
                        direct_host = domestic_index_host(current_index)
                        if direct_host and offline_env is None:
                            add_no_proxy_host(attempt_env, direct_host)
                            self.task_queue.put(
                                (
                                    "log",
                                    f"代理策略：{direct_host} 直连，其他地址保留系统代理。",
                                )
                            )
                        elif current_index and offline_env is None:
                            self.task_queue.put(
                                ("log", "代理策略：当前下载源沿用系统代理设置。")
                            )
                        if attempt > 1:
                            self.task_queue.put(
                                (
                                    "log",
                                    f"\n[自动重试 {attempt}/{len(attempt_indexes)}] "
                                    f"切换下载源：{current_index}",
                                )
                            )
                        recent_output: list[str] = []
                        self.running_process = subprocess.Popen(
                            command,
                            cwd=str(cwd),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            bufsize=1,
                            env=attempt_env,
                            creationflags=creation_flags(),
                        )
                        assert self.running_process.stdout is not None
                        # Cancellation can arrive while Popen is creating the child.
                        if self.cancel_requested:
                            self.cancel_task()
                        for line in self.running_process.stdout:
                            rendered = line.rstrip()
                            recent_output.append(rendered)
                            if len(recent_output) > 200:
                                recent_output.pop(0)
                            self.task_queue.put(("log", rendered))
                        return_code = self.running_process.wait()
                        self.running_process = None
                        if self.cancel_requested:
                            raise InterruptedError("任务已取消")
                        if return_code == 0:
                            if current_index in active_indexes:
                                active_indexes.remove(current_index)
                                active_indexes.insert(0, current_index)
                            break
                        output = "\n".join(recent_output)
                        can_retry = (
                            attempt < len(attempt_indexes)
                            and is_network_failure(output)
                        )
                        if can_retry:
                            self.task_queue.put(
                                ("log", "检测到网络/TLS 错误，准备切换下载源。")
                            )
                            continue
                        raise RuntimeError(f"命令执行失败，退出代码：{return_code}")
                self.task_queue.put(("done", True, f"{title}完成"))
            except InterruptedError as exc:
                self.task_queue.put(("done", False, str(exc), "cancelled"))
            except Exception as exc:
                self.task_queue.put(("done", False, str(exc), "error"))
            finally:
                self.running_process = None

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()


    def _format_command(self, command: list[str]) -> str:
        return subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)


    def _reset_project_settings(self, project: Path) -> None:
        self.entry_var.set("")
        self.output_name_var.set("")
        self._set_icon_values("", "")
        self.python_version_var.set("系统默认（最快）")
        self.pyinstaller_version_var.set("自动")
        self.package_mode_var.set("单文件（--onefile）")
        self.window_mode_var.set("显示命令行窗口（--console）")
        self.preset_var.set("标准（推荐）")
        self.clean_var.set(True)
        self.delete_cache_after_build_var.set(True)
        self.hidden_imports_var.set("")
        self.excludes_var.set("")
        self.exclude_dev_var.set(False)
        self.auto_collect_data_var.set(True)
        self.extra_args_text.delete("1.0", "end")
        self._apply_project_defaults(project)


    def _apply_project_settings_data(self, data: dict) -> None:
        mapping = {
            "entry": self.entry_var,
            "output_name": self.output_name_var,
            "dist": self.dist_var,
            "python_version": self.python_version_var,
            "pyinstaller_version": self.pyinstaller_version_var,
            "package_mode": self.package_mode_var,
            "window_mode": self.window_mode_var,
            "preset": self.preset_var,
            "requirements": self.requirements_var,
            "hidden_imports": self.hidden_imports_var,
            "excludes": self.excludes_var,
        }
        for key, variable in mapping.items():
            value = data.get(key)
            if isinstance(value, str):
                variable.set(value)
        path, text = data.get("icon"), data.get("icon_text")
        self._set_icon_values(path if isinstance(path, str) else "", text if isinstance(text, str) else "")

        legacy_window_modes = {
            "控制台程序（--console）": "显示命令行窗口（--console）",
            "窗口程序（--windowed）": "不显示命令行窗口（--windowed）",
        }
        self.window_mode_var.set(
            legacy_window_modes.get(
                self.window_mode_var.get(), self.window_mode_var.get()
            )
        )
        if self.package_mode_var.get() == LEGACY_SYSTEM_PYTHON_PACKAGE_MODE:
            self.package_mode_var.set(SYSTEM_PYTHON_PACKAGE_MODE)
        if self.python_version_var.get() == "系统默认":
            self.python_version_var.set("系统默认（最快）")

        boolean_defaults = {
            "clean": (self.clean_var, True),
            "delete_cache_after_build": (
                self.delete_cache_after_build_var,
                True,
            ),
            "exclude_dev": (self.exclude_dev_var, False),
            "auto_collect_data": (self.auto_collect_data_var, True),
        }
        for key, (variable, default) in boolean_defaults.items():
            if key in data:
                variable.set(data[key] if isinstance(data[key], bool) else default)
            else:
                variable.set(default)

        self.extra_args_text.delete("1.0", "end")
        extra_args = data.get("extra_args")
        if isinstance(extra_args, str) and extra_args:
            self.extra_args_text.insert("1.0", extra_args)


    def _portable_project_value(self, project: Path, value: str) -> str:
        stripped = value.strip().strip('"')
        if not stripped:
            return ""
        path = Path(stripped).expanduser()
        if not path.is_absolute():
            return stripped
        try:
            return path.resolve().relative_to(project.resolve()).as_posix()
        except ValueError:
            return str(path)


    def _render_icon(self, text, path):
        if not getattr(self, 'preview_only', False):
            render_text_icon(text, path)

    def cancel_task(self):
        self.cancel_requested = True
        process = self.running_process
        if process is None or process.poll() is not None:
            return
        try:
            if os.name == 'nt':
                result = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
                if result.returncode != 0 and process.poll() is None:
                    process.kill()
            else:
                process.terminate()
        except (OSError, subprocess.SubprocessError):
            try:
                process.kill()
            except OSError:
                pass
