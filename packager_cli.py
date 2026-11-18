"""Headless CLI using the same planner and execution engine as the GUI."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import queue
import subprocess
import sys

from packager_core import (
    APP_DIR,
    APP_VERSION,
    BUNDLE_DIR,
    ENTRY_PRIORITIES,
    GENERATED_REQUIREMENTS_MARKER,
    SYSTEM_PYTHON_ENTRY_ONLY_MODE,
    SYSTEM_PYTHON_PACKAGE_MODE,
    SYSTEM_PYTHON_SOURCE_ONLY_MODE,
    PackagerController,
    dependency_output_path,
    project_settings_path,
    is_generated_requirements,
    locate_uv,
    scan_local_requirements,
    uv_cache_directory,
)
from system_python_launcher import build_system_python_launcher


class Value:
    def __init__(self, value=''):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class TextValue:
    def __init__(self):
        self.value = ''
    def get(self, *_):
        return self.value
    def delete(self, *_):
        self.value = ''
    def insert(self, index, value):
        self.value = value + self.value if index == '1.0' else self.value + value


class ConsoleDialogs:
    @staticmethod
    def showerror(title, message):
        raise ValueError(message)
    showwarning = showerror
    @staticmethod
    def askyesno(title, message):
        raise ValueError(message + '\nCLI 不进行交互确认；请修正路径或用 --no-requirements 明确跳过依赖。')


MODES = {'onefile': '单文件（--onefile）', 'onedir': '目录模式（--onedir）',
         'system': SYSTEM_PYTHON_PACKAGE_MODE, 'source': SYSTEM_PYTHON_SOURCE_ONLY_MODE,
         'entry': SYSTEM_PYTHON_ENTRY_ONLY_MODE}
PRESETS = {'standard': '标准（推荐）', 'slim': '精简优先（排除开发工具）',
           'compatible': '兼容优先（禁用 UPX）', 'debug': '导入调试（输出详细信息）'}


class ConsoleController(PackagerController):
    def __init__(self, project: Path, *, preview=False):
        self.dialogs = ConsoleDialogs()
        self.preview_only = preview
        self.active_project_path = project
        for name in ('entry output_name icon icon_text dist python_version pyinstaller_version package_mode '
                     'window_mode preset clean '
                     'delete_cache_after_build requirements hidden_imports '
                     'excludes exclude_dev auto_collect_data').split():
            setattr(self, name+'_var', Value())
        self.extra_args_text = TextValue()
        self._reset_project_settings(project)
        self.uv_path = locate_uv()
        self.worker_thread = None
        self.running_process = None
        self.cancel_requested = False
        self.task_queue = queue.Queue()
        self.task_success_callback = None

    def _set_icon_values(self, path, text):
        self.icon_var.set(path)
        self.icon_text_var.set(text)
    def _icon_values(self):
        return self.icon_var.get().strip().strip('"'), self.icon_text_var.get().strip()
    def _project_path(self, required=True):
        return self.active_project_path
    def _set_busy(self, busy, status):
        pass
    def _task_started(self, title):
        pass
    def append_log(self, message):
        print(message, file=sys.stderr, flush=True)
    def _ensure_uv(self):
        if self.uv_path:
            return True
        if self.preview_only:
            self.uv_path = Path('uv')
            return True
        raise ValueError('未找到 uv，请先安装 uv 并加入 PATH。预览命令不需要 uv。')

    def load(self, args):
        project = self.active_project_path
        config = Path(args.config).expanduser().resolve() if args.config else project_settings_path(APP_DIR, project)
        config_requirements = False
        loaded_config = not args.no_config and (config.exists() or args.config)
        if loaded_config:
            data = json.loads(config.read_text(encoding='utf-8-sig'))
            if not isinstance(data, dict):
                raise ValueError('项目配置必须是 JSON 对象。')
            config_requirements = 'requirements' in data
            self._apply_project_settings_data(data)
        for arg, variable in {'entry': 'entry', 'name': 'output_name', 'output': 'dist', 'requirements': 'requirements',
                              'icon': 'icon', 'icon_text': 'icon_text', 'python': 'python_version',
                              'pyinstaller_version': 'pyinstaller_version'}.items():
            value = getattr(args, arg, None)
            if value is not None:
                getattr(self, variable+'_var').set(value)
        for arg, mapping, variable in (('mode', MODES, 'package_mode'), ('preset', PRESETS, 'preset')):
            value = getattr(args, arg, None)
            if value is not None:
                getattr(self, variable+'_var').set(mapping[value])
        for arg, variable in (('clean', 'clean'), ('delete_cache', 'delete_cache_after_build'),
                              ('auto_collect_data', 'auto_collect_data'), ('exclude_dev', 'exclude_dev')):
            value = getattr(args, arg, None)
            if value is not None:
                getattr(self, variable+'_var').set(value)
        if getattr(args, 'windowed', None) is not None:
            self.window_mode_var.set('不显示命令行窗口（--windowed）' if args.windowed else '显示命令行窗口（--console）')
        for arg, variable in (('hidden_import', 'hidden_imports'), ('exclude', 'excludes')):
            values = getattr(args, arg, None)
            if values is not None:
                getattr(self, variable+'_var').set(','.join(values))
        if getattr(args, 'extra_arg', None) is not None:
            self.extra_args_text.value = '\n'.join(args.extra_arg)
        if getattr(args, 'no_requirements', False):
            self.requirements_var.set('')
        elif not args.requirements and not config_requirements:
            selected = Path(self.requirements_var.get())
            if not selected.is_file():
                self.requirements_var.set('')
        if getattr(args, 'export', False):
            return
        if not self.entry_var.get():
            candidates = [project / name for name in ENTRY_PRIORITIES if (project / name).is_file()]
            if not candidates:
                candidates = sorted(project.glob('*.py')) + sorted(project.glob('*.pyw'))
            if not candidates:
                raise ValueError('项目根目录没有 Python 入口，请用 --entry 指定。')
            self.entry_var.set(str(candidates[0].relative_to(project)))
        entry = self._entry_path(project)
        if args.entry and not getattr(args, 'name', None):
            self.output_name_var.set(entry.stem)
        if not self.output_name_var.get():
            self.output_name_var.set(entry.stem)
        if self.package_mode_var.get() not in MODES.values():
            raise ValueError('配置中的打包模式无效；请用 --mode 覆盖。')

    def wait(self):
        interrupted = False
        while True:
            try:
                event = self.task_queue.get(timeout=.1)
                if event[0] == 'log':
                    self.append_log(event[1])
                elif event[0] == 'done':
                    self.worker_thread.join()
                    if interrupted or (len(event) > 3 and event[3] == 'cancelled'):
                        return 130
                    if not event[1]:
                        raise RuntimeError(event[2])
                    return 0
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                interrupted = True
                self.cancel_task()


def parser():
    result = argparse.ArgumentParser(
        description="Python 精简打包工具。无参数启动 GUI，子命令可在终端执行。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例\n"
            "  python main.py build --help\n"
            '  python main.py preview "D:\\项目" --mode entry --json\n'
            '  python main.py build "D:\\项目" --mode entry --windowed'
        ),
    )
    result.add_argument('--version', action='version', version=APP_VERSION)
    commands = result.add_subparsers(dest='command', required=True)
    commands.add_parser('gui', help='启动图形界面')
    doctor = commands.add_parser('doctor', help='检查 Python、uv 和资源文件')
    doctor.add_argument('--json', action='store_true')
    for command, help_text in (('scan', '扫描/锁定/导出运行依赖'), ('preview', '预览打包计划，不构建'), ('build', '执行打包')):
        p = commands.add_parser(command, help=help_text)
        p.add_argument('project', type=Path, help='项目目录；相对路径以调用目录为基准')
        p.add_argument('--entry', help='相对项目目录的入口文件')
        p.add_argument('--config', help='指定配置文件；相对调用目录')
        p.add_argument('--no-config', action='store_true', help='忽略已有项目配置')
        p.add_argument('--requirements', help='依赖文件；相对项目目录')
        p.add_argument('--python', help='Python 版本，如 3.11')
        p.add_argument('--json', action='store_true', help='stdout 输出 JSON，日志写入 stderr')
        if command == 'scan':
            p.add_argument('--lock', action='store_true', help='使用 uv 锁定版本')
            p.add_argument('--export', action='store_true', help='用 uv 导出 pyproject.toml')
            continue
        p.add_argument('--name')
        p.add_argument('--output', help='输出目录；相对项目目录')
        p.add_argument('--mode', choices=MODES,
                       help='onefile 单个独立 EXE，onedir 独立目录，system 启动器内置资源，'
                            'source 启动器外置资源，entry 仅包装入口')
        p.add_argument('--preset', choices=PRESETS)
        window = p.add_mutually_exclusive_group()
        window.add_argument('--windowed', dest='windowed', action='store_true', default=None)
        window.add_argument('--console', dest='windowed', action='store_false')
        p.add_argument('--no-requirements', action='store_true')
        p.add_argument('--icon')
        p.add_argument('--icon-text')
        p.add_argument('--pyinstaller-version')
        p.add_argument('--hidden-import', action='append')
        p.add_argument('--exclude', action='append')
        p.add_argument('--extra-arg', action='append', help='每次一个参数，如 --extra-arg=--noupx')
        for flag in ('clean', 'delete-cache', 'auto-collect-data', 'exclude-dev'):
            p.add_argument('--'+flag, action=argparse.BooleanOptionalAction, default=None)
        if command == 'build':
            p.add_argument('--dry-run', action='store_true', help='只预览，不生成文件')
    return result


def emit(data, as_json):
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        for key, value in data.items():
            print(f'{key}: {value}')


def main(argv=None):
    # Deterministic, readable Chinese output when invoked from scripts or pipes.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    args = parser().parse_args(argv)
    try:
        if args.command == 'gui':
            from packager_gui import launch_gui
            launch_gui()
            return 0
        if args.command == 'doctor':
            uv = locate_uv()
            emit({'version': APP_VERSION, 'python': sys.executable, 'uv': uv,
                  'app_dir': APP_DIR, 'bundle_dir': BUNDLE_DIR,
                  'uv_cache': uv_cache_directory(uv), 'third_party_runtime_dependencies': ['tkwebui'], 'platform': sys.platform}, args.json)
            return 0
        if args.config and args.no_config:
            raise ValueError('--config 与 --no-config 不能同时使用。')
        project = args.project.expanduser().resolve()
        if not project.is_dir():
            raise ValueError(f'项目目录不存在：{project}')
        preview = args.command == 'preview' or getattr(args, 'dry_run', False)
        app = ConsoleController(project, preview=preview)
        app.load(args)
        if args.command == 'scan':
            if args.lock and args.export:
                raise ValueError('--lock 和 --export 不能同时使用。')
            target, redirected = dependency_output_path(project, app.requirements_var.get())
            if args.lock or args.export:
                app._ensure_uv()
            uv = str(app.uv_path)
            steps = []
            count, unreadable = 0, []
            if args.export:
                if not (project / 'pyproject.toml').is_file():
                    raise ValueError('项目缺少 pyproject.toml。')
                steps.append(('导出依赖', [uv, 'export', '--project', str(project), '--format', 'requirements-txt',
                              '--no-dev', '--no-emit-project', '--output-file', str(target)], project))
            else:
                scan_target = target.with_suffix('.in') if args.lock else target
                if scan_target.exists() and not is_generated_requirements(scan_target):
                    raise ValueError(f'不会覆盖手写依赖文件：{scan_target}')
                count, unreadable = scan_local_requirements(project, app._entry_path(project), scan_target)
                if args.lock:
                    cmd = [uv, 'pip', 'compile', str(scan_target), '--output-file', str(target), '--no-header']
                    version = app.python_version_var.get()
                    if version and not version.startswith('系统默认'):
                        cmd += ['--python-version', version]
                    steps.append(('锁定依赖', cmd, project))
            if steps:
                app._run_task('生成依赖', steps)
                code = app.wait()
                if code:
                    return code
                target.write_text(GENERATED_REQUIREMENTS_MARKER+'\n'+target.read_text(encoding='utf-8-sig'), encoding='utf-8')
            emit({'requirements': target, 'scanned_files': count, 'unreadable': unreadable, 'redirected': redirected}, args.json)
            return 0
        if app._is_system_python_mode():
            settings = app._system_launcher_settings()
            plan = {'engine': 'system-python', **asdict(settings)}
            if not settings.entry_only:
                plan.pop('entry_only')
        else:
            command, cwd, dist = app._build_command()
            plan = {'engine': 'pyinstaller', 'environment': app.build_environment, 'argv': command, 'cwd': cwd, 'output': dist,
                    'command': subprocess.list2cmdline(command)}
        if preview:
            emit(plan, args.json)
            return 0
        if plan['engine'] == 'system-python':
            def operation():
                build_system_python_launcher(project=settings.project, entry=settings.entry, output=settings.output,
                    title=settings.name, console=settings.console, source_only=settings.source_only,
                    entry_only=settings.entry_only,
                    icon_path=settings.icon, log=app.append_log, cancelled=lambda: app.cancel_requested)
            app._run_callable_task('生成系统 Python 启动器', operation)
            protected = settings.output
        else:
            dist.mkdir(parents=True, exist_ok=True)
            app._run_task('打包项目', [(app.build_environment, command, cwd)])
            protected = dist
        code = app.wait()
        if code:
            return code
        warning = None
        if app.delete_cache_after_build_var.get():
            warning = app._delete_build_work_cache(project, system_launcher=app._is_system_python_mode(), protected_path=protected)
        emit({'success': True, 'output': protected, 'cleanup_warning': warning}, args.json)
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, RuntimeError) as exc:
        if getattr(args, 'json', False):
            emit({'success': False, 'error': str(exc)}, True)
        print(f'错误：{exc}', file=sys.stderr)
        return 2 if isinstance(exc, ValueError) else 1


if __name__ == '__main__':
    raise SystemExit(main())
