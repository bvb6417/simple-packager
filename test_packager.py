"""Regression tests. No PyInstaller, compiler or EXE generation is invoked."""
import contextlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zlib
from unittest.mock import Mock, patch

import packager_core as core
import packager_cli as cli
from native_icon import render_text_icon
from system_python_launcher import PROJECT_SETTINGS_DIRECTORY, PROJECT_SETTINGS_FILENAME, collect_project_files

ROOT = Path(__file__).resolve().parent


def decode_generated_png(data):
    """Inspect actual RGBA pixels, not just the ICO/PNG file headers."""
    pos, compressed = 8, bytearray()
    while pos < len(data):
        length = struct.unpack('>I', data[pos:pos+4])[0]
        kind, payload = data[pos+4:pos+8], data[pos+8:pos+8+length]
        if kind == b'IHDR':
            width, height = struct.unpack('>II', payload[:8])
        elif kind == b'IDAT':
            compressed.extend(payload)
        pos += length+12
    raw = zlib.decompress(compressed)
    rows = []
    for y in range(height):
        start = y*(width*4+1)
        if raw[start] != 0:
            raise AssertionError('Unexpected PNG filter')
        rows.append(raw[start+1:start+1+width*4])
    return width, height, b''.join(rows)


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='packager-test-')
        self.project = Path(self.temp.name).resolve() / '中文 项目'
        self.project.mkdir()
        (self.project / 'main.py').write_text('print("hello")\n', encoding='utf-8')
    def tearDown(self):
        self.temp.cleanup()
    def call(self, *args):
        return subprocess.run([sys.executable, str(ROOT/'main.py'), *map(str, args)], cwd=self.temp.name,
                              text=True, encoding='utf-8', capture_output=True, timeout=30)
    def controller(self):
        app = cli.ConsoleController(self.project, preview=True)
        app.entry_var.set('main.py')
        app.output_name_var.set('中文 app')
        app.requirements_var.set('')
        return app

    def test_cli_help_and_doctor_from_other_cwd(self):
        self.assertEqual(self.call('--help').returncode, 0)
        result = self.call('doctor', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(json.loads(result.stdout)['app_dir']), ROOT)

    def test_headless_without_tk_or_pillow(self):
        script = '''import sys, importlib.abc
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in ('tkinter', 'PIL'): raise ImportError(fullname)
sys.meta_path.insert(0, Block())
from packager_cli import main
raise SystemExit(main(['preview', sys.argv[1], '--no-config', '--json']))
'''
        result = subprocess.run([sys.executable, '-c', script, str(self.project)], cwd=ROOT,
                                text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_five_preview_modes_no_side_effects(self):
        before = sorted(p.relative_to(self.project) for p in self.project.rglob('*'))
        for mode in cli.MODES:
            result = self.call('preview', self.project, '--mode', mode, '--icon-text', '包', '--json')
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data['engine'], 'system-python' if mode in ('system', 'source', 'entry') else 'pyinstaller')
        self.assertEqual(before, sorted(p.relative_to(self.project) for p in self.project.rglob('*')))

    def test_existing_config_and_overrides(self):
        (self.project/PROJECT_SETTINGS_FILENAME).write_text(json.dumps({'entry':'main.py', 'output_name':'saved',
            'relative_path_mode':'EXE 所在目录（适合外置配置/数据库/日志）', 'package_mode':core.LEGACY_SYSTEM_PYTHON_PACKAGE_MODE, 'clean':'false', 'dist':'out'}), encoding='utf-8-sig')
        config = self.project / PROJECT_SETTINGS_FILENAME
        result = self.call('preview', self.project, '--config', config,
                           '--name', '覆盖', '--mode', 'onedir', '--windowed', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIn('--onedir', data['argv'])
        self.assertIn('--windowed', data['argv'])
        self.assertIn('覆盖', data['argv'])
        self.assertNotIn('--runtime-hook', data['argv'])
        self.assertEqual(Path(data['output']), self.project/'out')
        self.assertEqual(self.call('preview', self.project, '--no-config', '--json').returncode, 0)

    def test_central_settings_are_shared_with_cli_and_isolated_by_project_path(self):
        tool = Path(self.temp.name) / "tool"
        second = Path(self.temp.name) / "other" / self.project.name
        second.mkdir(parents=True)
        (second / "main.py").touch()
        first_config = core.project_settings_path(tool, self.project)
        second_config = core.project_settings_path(tool, second)
        self.assertNotEqual(first_config, second_config)
        legacy = self.project / PROJECT_SETTINGS_FILENAME
        legacy.write_text('{"output_name":"legacy"}', encoding="utf-8")
        explicit = Path(self.temp.name) / "explicit.json"
        explicit.write_text('{"output_name":"explicit"}', encoding="utf-8")

        def output_name(project, *flags):
            with patch.object(cli, "APP_DIR", tool), contextlib.redirect_stdout(io.StringIO()) as out:
                status = cli.main(["preview", str(project), "--mode", "source", "--json", *flags])
            self.assertEqual(status, 0, out.getvalue())
            return json.loads(out.getvalue())["name"]

        self.assertEqual(output_name(self.project), "main")
        self.assertEqual(output_name(self.project, "--config", str(legacy)), "legacy")
        self.assertFalse(first_config.parent.exists())
        first_config.parent.mkdir(parents=True)
        first_config.write_text('{"output_name":"first"}', encoding="utf-8")
        second_config.write_text('{"output_name":"second"}', encoding="utf-8")
        self.assertEqual(output_name(self.project), "first")
        self.assertEqual(output_name(second), "second")
        self.assertEqual(output_name(self.project, "--config", str(explicit)), "explicit")
        self.assertEqual(output_name(self.project, "--no-config"), "main")
        self.assertEqual(legacy.read_text(encoding="utf-8"), '{"output_name":"legacy"}')

    def test_reserved_names_and_missing_inputs(self):
        for name in ('CON', 'aux.exe', 'LPT1', 'a.', 'a ', '..', 'a/b'):
            result = self.call('preview', self.project, '--name', name, '--json')
            self.assertEqual(result.returncode, 2, (name, result.stdout, result.stderr))
            self.assertFalse(json.loads(result.stdout)['success'])
        result = self.call('preview', self.project, '--requirements', 'missing.txt', '--json')
        self.assertEqual(result.returncode, 2)
        legacy = self.project / PROJECT_SETTINGS_FILENAME
        legacy.write_text('broken')
        self.assertEqual(self.call('preview', self.project, '--json').returncode, 0)
        self.assertEqual(self.call('preview', self.project, '--config', legacy, '--json').returncode, 2)

    def test_handwritten_requirements_preserved(self):
        target = self.project / core.DEFAULT_REQUIREMENTS_NAME
        target.write_text('my-pinned-library==1.0\n')
        (self.project/'main.py').write_text('import docx\nimport json\n', encoding='utf-8')
        result = self.call('scan', self.project, '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data['redirected'])
        self.assertEqual(target.read_text(), 'my-pinned-library==1.0\n')
        self.assertIn('python-docx', Path(data['requirements']).read_text(encoding='utf-8'))

    def test_src_relative_pyd_and_source_encoding(self):
        src = self.project / 'src'
        src.mkdir()
        (src/'mypkg').mkdir()
        (src/'mypkg'/'__init__.py').write_text('from . import child\n')
        (src/'mypkg'/'child.py').write_bytes('# coding: gbk\n# 中文\nimport yaml\n'.encode('gbk'))
        (self.project/'native.cp311-win_amd64.pyd').write_bytes(b'test')
        (self.project/'unused.py').write_text('import should_not_appear\n')
        (self.project/'main.py').write_text('import sys\nsys.path.insert(0, "src")\nimport mypkg\nimport native\n')
        result = core.scan_imports(self.project, self.project/'main.py')
        self.assertIn('yaml', result.imported_modules)
        self.assertNotIn('native', result.imported_modules)
        self.assertNotIn('should_not_appear', result.imported_modules)
        self.assertEqual(result.unreadable, [])
        self.assertIn(src, result.source_roots)

    def test_private_tk_keeps_runtime_layout_and_respects_auto_collect(self):
        app = self.controller()
        runtime = self.project / "runtime"
        for relative in ("bin/tcl86t.dll", "bin/tk86t.dll", "lib/tcl8.6/init.tcl", "lib/tk8.6/tk.tcl"):
            path = runtime / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

        def collected():
            command, _, _ = app._build_command()
            return {command[i + 1] for i, arg in enumerate(command) if arg == "--add-data"}

        expected = {f"{runtime / 'bin' / name}{os.pathsep}runtime/bin" for name in ("tk86t.dll", "tcl86t.dll")}
        expected.update(f"{runtime / 'lib' / name}{os.pathsep}runtime/lib/{name}" for name in ("tk8.6", "tcl8.6"))
        self.assertTrue(expected.issubset(collected()))
        app.auto_collect_data_var.set(False)
        self.assertFalse(expected & collected())
        app.auto_collect_data_var.set(True)
        (runtime / "lib/tk8.6/tk.tcl").unlink()
        self.assertFalse(expected & collected())

    def test_managed_options_cannot_override_cleanup_paths(self):
        app = self.controller()
        app.extra_args_text.value = '--distpath=.uv-packager/result'
        with self.assertRaises(ValueError):
            app._build_command()

    def test_cleanup_protects_output_inside_cache(self):
        app = self.controller()
        cache = self.project/'.uv-packager'
        cache.mkdir()
        output = cache/'result.txt'
        output.write_text('keep')
        warning = app._delete_build_work_cache(self.project, system_launcher=False, protected_path=output)
        self.assertIsNotNone(warning)
        self.assertTrue(output.is_file())

    def test_launcher_collection_excludes_output_and_cache(self):
        (self.project/'dist').mkdir()
        (self.project/'dist'/'old.txt').write_text('old')
        (self.project/'asset.txt').write_text('asset')
        settings_folder = self.project / PROJECT_SETTINGS_DIRECTORY
        settings_folder.mkdir()
        (settings_folder / "project-a.json").write_text("{}", encoding="utf-8")
        paths = {rel.as_posix() for _, rel in collect_project_files(self.project, self.project/'dist')}
        self.assertIn('asset.txt', paths)
        self.assertNotIn('dist/old.txt', paths)
        self.assertNotIn(f'{PROJECT_SETTINGS_DIRECTORY}/project-a.json', paths)
        source = {rel.as_posix() for _, rel in collect_project_files(self.project, source_only=True)}
        self.assertEqual(source, {'main.py'})

    def test_source_launcher_publishes_only_exe_and_preserves_existing_files(self):
        from system_python_launcher import build_system_python_launcher
        import zipfile
        entry = self.project / 'main.py'
        asset = self.project / 'images' / 'test.bin'
        asset.parent.mkdir()
        asset.write_bytes(b'first')
        output = self.project / 'dist' / 'test.exe'
        def build():
            return build_system_python_launcher(project=self.project, entry=entry, output=output,
                title='test', console=True, source_only=True)
        build()
        with zipfile.ZipFile(output) as archive:
            self.assertEqual([k for k in archive.namelist() if k.startswith('payload/')], ['payload/main.py'])
        self.assertEqual(list(output.parent.iterdir()), [output])
        previous_resource = output.parent / 'images' / asset.name
        previous_resource.parent.mkdir()
        previous_resource.write_bytes(b'local')
        build()
        self.assertEqual(previous_resource.read_bytes(), b'local')
        self.assertEqual(asset.read_bytes(), b'first')

    @unittest.skipUnless(os.name == "nt", "Windows launcher")
    def test_entry_wrapper_embeds_only_entry_and_runs_with_external_sibling(self):
        import zipfile

        source = self.project / "src"
        source.mkdir()
        (source / "helper.py").write_text("VALUE = 42\n", encoding="utf-8")
        (source / "entry.pyw").write_text(
            "from pathlib import Path\nfrom helper import VALUE\nimport sys\n"
            "Path(__file__).with_name('result.txt').write_text(f'{VALUE} {sys.argv[1]}')\n",
            encoding="utf-8",
        )

        args = ("--mode", "entry", "--entry", "src/entry.pyw", "--name", "wrapped",
                "--output", ".", "--windowed", "--icon-text", "📦", "--json")
        preview = self.call("preview", self.project, *args)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertTrue(json.loads(preview.stdout)["entry_only"])
        build = self.call("build", self.project, *args)
        self.assertEqual(build.returncode, 0, build.stderr)
        output = Path(json.loads(build.stdout)["output"])
        with zipfile.ZipFile(output) as archive:
            self.assertEqual([name for name in archive.namelist() if name.startswith("payload/")],
                             ["payload/src/entry.pyw"])
            config = json.loads(archive.read("__launcher__/config.json"))
            self.assertTrue(config["entry_only"])
            self.assertFalse(config["console"])

        # Leave only the external helper under src before running the executable.
        (source / "entry.pyw").rename(source / "entry.original")
        env = {**os.environ, "LOCALAPPDATA": self.temp.name}
        # Exercise the same Python ZIP entry as the native stub.
        run = subprocess.run([sys.executable, str(output), "argument"], cwd=self.temp.name,
                             env=env, capture_output=True, timeout=12)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual((source / "result.txt").read_text(), "42 argument")

    def test_independent_build_always_isolates(self):
        app = self.controller()
        req = self.project / "requirements.txt"
        req.write_text("packaging>=19\n", encoding="utf-8")
        app.requirements_var.set(str(req))
        for mode in ("单文件（--onefile）", "目录模式（--onedir）"):
            app.package_mode_var.set(mode)
            command, _, _ = app._build_command()
            self.assertEqual(command[1:4], ["tool", "run", "--isolated"])
            self.assertIn("pyinstaller==" + core.DEFAULT_PYINSTALLER_VERSION, command)
            self.assertEqual(Path(command[command.index("--with-requirements") + 1]), req)
        app.pyinstaller_version_var.set("6.14.2")
        self.assertIn("pyinstaller==6.14.2", app._build_command()[0])

    def test_cross_mirror_cache_is_reused_offline(self):
        app = self.controller()
        app.uv_path = Path("uv.exe")
        attempts = []

        def launch(command, **kwargs):
            env = kwargs["env"]
            attempts.append((command, env))
            process = Mock()
            process.stdout = []
            process.wait.return_value = int("UV_INDEX" not in env)
            return process

        with patch.dict(os.environ, {"PYTHONPATH": "outside"}), \
             patch.object(core, "uv_cache_directory", return_value=self.project / "reported-uv-cache"), \
             patch.object(subprocess, "Popen", side_effect=launch), contextlib.redirect_stderr(io.StringIO()):
            for key in ("UV_INDEX", "UV_CACHE_DIR", "UV_TOOL_DIR", "UV_PYTHON_INSTALL_DIR"):
                os.environ.pop(key, None)
            cmd = ["uv.exe", "tool", "run", "--isolated", "pyinstaller", "--noconfirm", "main.py"]
            app._run_task("打包", [("PyInstaller", cmd, self.project)])
            self.assertEqual(app.wait(), 0)
        self.assertEqual([env["UV_DEFAULT_INDEX"] for _, env in attempts[:4]], list(core.INDEX_URLS))
        self.assertEqual(attempts[-2][0][-1], "--version")
        self.assertEqual(attempts[-1][0], cmd)
        self.assertEqual(attempts[-1][1]["UV_INDEX"].split(), list(core.INDEX_URLS[:-1]))
        self.assertTrue(all(env["UV_OFFLINE"] == "1" for _, env in attempts))
        for key in ("UV_CACHE_DIR", "UV_TOOL_DIR", "UV_PYTHON_INSTALL_DIR"):
            self.assertTrue(all(key not in env for _, env in attempts))
        self.assertTrue(all("PYTHONPATH" not in env for _, env in attempts))

    def test_automatic_mirrors_ignore_legacy_project_settings(self):
        app = self.controller()
        app._apply_project_settings_data({'index_source': 'https://old.invalid', 'bypass_domestic_proxy': False})
        app.uv_path = Path("uv.exe")
        attempts = []

        def launch(command, **kwargs):
            env = kwargs['env']
            attempts.append((env['UV_DEFAULT_INDEX'], env['NO_PROXY'].split(',')))
            process = Mock()
            process.stdout = ['connection reset'] if len(attempts) < 4 else []
            process.wait.return_value = 1 if process.stdout else 0
            return process

        with patch.dict(os.environ, {'NO_PROXY': 'localhost', 'no_proxy': 'localhost'}), \
             patch.object(core, 'uv_cache_directory', return_value=None), \
             patch.object(subprocess, 'Popen', side_effect=launch), contextlib.redirect_stderr(io.StringIO()):
            app._run_task('test', [('uv', [str(app.uv_path), 'export'], self.project)])
            self.assertEqual(app.wait(), 0)
        self.assertEqual([url for url, hosts in attempts], list(core.INDEX_URLS))
        for url, hosts in attempts[:-1]:
            self.assertIn(core.domestic_index_host(url), hosts)
        self.assertEqual(attempts[-1][1], ['localhost'])

    def test_process_engine_success_failure_and_cancellation(self):
        app = self.controller()
        with contextlib.redirect_stderr(io.StringIO()):
            app._run_task('test', [('print', [sys.executable, '-c', 'print("ok")'], self.project)])
            self.assertEqual(app.wait(), 0)
            app._run_task('test', [('error', [sys.executable, '-c', 'raise SystemExit(7)'], self.project)])
            with self.assertRaises(RuntimeError):
                app.wait()
            app._run_task('test', [('wait', [sys.executable, '-c', 'import time; time.sleep(20)'], self.project)])
            started = time.monotonic()
            timer = threading.Timer(.3, app.cancel_task)
            timer.start()
            self.assertEqual(app.wait(), 130)
            timer.join()
            self.assertLess(time.monotonic()-started, 8)
            self.assertIsNone(app.running_process)

    def test_native_ico_has_seven_transparent_png_sizes(self):
        if os.name != 'nt':
            self.skipTest('Windows native renderer')
        for text in ('包', 'AI', '📦'):
            path = self.project / (text+'.ico')
            render_text_icon(text, path)
            data = path.read_bytes()
            self.assertEqual(struct.unpack('<HHH', data[:6]), (0, 1, 7))
            for i, size in enumerate((16, 24, 32, 48, 64, 128, 256)):
                w, h, _, _, _, depth, length, offset = struct.unpack('<BBBBHHII', data[6+i*16:22+i*16])
                self.assertEqual(w or 256, size)
                self.assertEqual(depth, 32)
                self.assertTrue(data[offset:offset+length].startswith(b'\x89PNG'))
                width, height, pixels = decode_generated_png(data[offset:offset+length])
                self.assertEqual((width, height), (size, size))
                self.assertIn(0, pixels[3::4])
                self.assertIn(255, pixels[3::4])
                if text == '📦':
                    colors = {tuple(channel//32 for channel in pixels[i:i+3])
                              for i in range(0, len(pixels), 4) if pixels[i+3] > 250}
                    self.assertGreaterEqual(len(colors), 4, f'{size}px lost emoji colors')

    def test_color_emoji_sequences_without_pillow(self):
        from color_renderer import render_color_text
        for text in ('🚀', '🌈', '👩\u200d💻', '包📦'):
            pixels, _, _ = render_color_text(text)
            colors = {tuple(channel//32 for channel in pixels[i:i+3])
                      for i in range(0, len(pixels), 4) if pixels[i+3] > 250}
            self.assertGreaterEqual(len(colors), 4, text)

    def test_build_dispatch_is_mocked_not_executed(self):
        # Verify build subcommand dispatch without ever invoking a packager.
        with patch.object(core.PackagerController, '_run_task') as task, patch.object(cli.ConsoleController, 'wait', return_value=0):
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(['build', str(self.project), '--no-delete-cache', '--json'])
            self.assertEqual(code, 0)
            self.assertEqual(task.call_args.args[1][0][1][-1], str(self.project/'main.py'))
        with patch.object(core.PackagerController, '_run_callable_task') as task, patch.object(cli.ConsoleController, 'wait', return_value=0):
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(['build', str(self.project), '--mode', 'source', '--no-delete-cache'])
            self.assertEqual(code, 0)
            task.assert_called_once()


if __name__ == '__main__':
    unittest.main(verbosity=2)
