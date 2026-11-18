# 精简打包

双击 `main.py` 打开界面，或使用下方 CLI。图形界面使用系统 Python 安装的 `tkwebui`，可用 `python -m pip install -r runtime-requirements.txt` 安装。独立打包通过 uv 在隔离环境中运行 PyInstaller。启动器模式使用目标电脑上的 Python。

## 命令行调用

PowerShell 中请用 `python .\main.py --help` 查看 CLI 帮助。可以将 `main.py` 换成绝对路径，从其他目录调用。

```powershell
python main.py --help
python main.py doctor --json
python main.py scan "D:\项目\示例" --entry main.py --json
python main.py preview "D:\项目\示例" --mode onefile --windowed --json
python main.py build "D:\项目\示例" --dry-run --mode system --json
```

打包器本身的 EXE 也能接收同样的子命令。使用带控制台的版本可在终端查看帮助、日志和 JSON。当前无控制台版本可执行子命令，需要查看输出时可用 `python main.py`。

手动执行实际构建：

```powershell
python main.py build "D:\项目\示例" --mode onefile --entry main.py --requirements runtime-requirements.txt --name 示例 --windowed
python main.py build "D:\项目\示例" --mode source --name 示例 --windowed
python main.py build "D:\项目\示例" --mode entry --entry main.py --icon-text 📦 --windowed
```

- `scan`：本地扫描；`--lock` 使用 uv 锁定版本；`--export` 从 `pyproject.toml` 导出。手写依赖文件保留，必要时写入 `runtime-requirements.generated.txt`。扫描未解析文件会通过 `unreadable` 返回。
- `preview` / `build --dry-run`：只输出计划；不构建、不生成图标、不创建工作目录，也不写配置。没有 uv 时仍可预览。
- `build`：执行构建，日志实时写入 stderr；Ctrl+C 取消。成功后按配置清理工作缓存，CLI 不自动打开目录。
- `--mode`：`onefile`（单文件）、`onedir`（目录）、`system`（系统 Python，内置完整项目）、`source`（系统 Python，仅源码，资源外置）、`entry`（系统 Python，仅包装入口）。
- 默认读取工具目录中该项目的配置。显式 CLI 参数覆盖配置，`--no-config` 忽略配置，`--config 文件` 指定配置。CLI 不改写项目配置。
- 项目目录相对于调用目录解析；`--entry`、`--output`、`--requirements`、`--icon` 相对于项目目录解析；`--config` 相对于调用目录解析。
- 可选：`--python 3.11`、`--pyinstaller-version 6.21.0`、`--preset standard|slim|compatible|debug`、`--icon 图标.ico`、`--icon-text 包`。
- `--hidden-import`、`--exclude`、`--extra-arg` 可重复，显式列表替换配置列表。例如 `--hidden-import my_plugin --extra-arg=--collect-data=my_package`。受管理的输出路径/名称/模式须通过对应参数指定。
- `--no-requirements` 明确跳过依赖文件；指定的依赖文件不存在时 CLI 返回错误，不弹窗询问。
- `--no-clean`、`--no-delete-cache`、`--no-auto-collect-data` 可关闭相应选项。
- `--json` 将结果写入 stdout，日志仍在 stderr，适合其他程序调用。退出码：0 成功，1 执行/IO失败，2 参数或配置错误，130 取消。

```python
import json
import subprocess
result = subprocess.run(
    ["python", r"D:\工具\simple-packager\main.py", "preview", r"D:\项目\示例", "--json"],
    capture_output=True, text=True, encoding="utf-8", check=True,
)
plan = json.loads(result.stdout)
print(plan)
```

## 主要功能

- 自动扫描项目中的 Python 文件，优先选择 `main.py`、`app.py`、`run.py` 等入口。
- 项目目录框支持从 Windows 资源管理器拖入文件夹；入口文件框支持拖入单个 `.py` 文件并自动识别项目目录。
- 在首页选择打包模式，通过滑动开关决定是否显示控制台。打包预设和其他 PyInstaller 参数位于折叠的高级选项。
- 可生成“系统 Python 启动器”：单文件 EXE 不内置 Python 和第三方包，直接使用系统 PATH 中的 `python.exe`。
- 每个项目的打包参数集中保存在工具目录下的 `项目打包配置` 文件夹。项目没有配置时使用默认选项。
- 使用内置 AST 扫描器分析实际 import，并识别项目内的 `.py`/`.pyd` 本地模块；快速模式不需要下载任何扫描工具。
- 内置清华、阿里云、腾讯云和官方 PyPI；TLS/连接失败时自动切换。
- 国内镜像默认写入 `NO_PROXY` 直连，官方 PyPI 和其他地址继续使用本地代理。
- 支持直接从 uv 项目的 `pyproject.toml` 导出运行依赖。
- 支持图标、隐藏导入、排除模块和其他 PyInstaller 参数。
- 窗口使用 📦 图标；打包图标既支持 `.ico` 文件，也支持直接输入 emoji 或短文本。
- 自动识别并收集 `ttkbootstrap` 等已知包的字体、图标等运行资源。
- 后台执行任务，实时显示日志，可以中途停止。
- CLI 的 `preview` 显示实际打包环境。PyInstaller 版本设置为“自动”时使用工具自带的默认版本，填写具体版本会保留该约束。

## 使用方法

1. 双击项目根目录的 `main.py`（使用系统 Python）。
2. 选择项目目录，工具会自动寻找入口文件。
3. 在打包页选择依赖生成方式并点击扫描图标。旁边的查看按钮可打开依赖文件。
4. 选择打包模式，并设定是否显示控制台。图形界面使用运行打包器的 Python。PyInstaller 由 uv 按打包器设定的默认版本准备。
5. 点击“开始打包”。成功后自动打开输出目录，运行中的任务可以用同一按钮停止。

如果希望生成依赖目标电脑本机环境的小体积 EXE，可以选择“系统 Python 启动器（完整项目，内置资源）”或“系统 Python 启动器（仅源码，资源外置）”。这两种模式和“入口包装”都直接使用系统 Python，构建无需 uv。

第一次运行时如果没有安装 uv，可以点击打包页 uv 旁的下载图标安装 uv。该按钮会在确认后调用 Astral 官方安装脚本。

Python 版本默认使用本机解释器，启动最快。只有明确选择 3.10～3.14 时，uv 才会在本机缺少对应版本的情况下下载一套受管理的 Python。

## 依赖文件

默认“本地快速扫描”只生成 `runtime-requirements.txt`，不联网、不下载扫描工具或目标项目依赖。

“锁定版本”会生成两个文件：

- `runtime-requirements.in`：根据源码 import 得到的直接依赖。
- `runtime-requirements.txt`：uv 解析后的完整锁定依赖；此步骤需要访问包索引。

依赖扫描无法百分之百识别字符串导入、插件系统或运行时动态加载。如果打包后提示缺少模块，请在“高级选项 → 隐藏导入”中补充模块名。

源码中的 import 名不一定等于 PyPI/pip 发行包名，例如 `docx` 对应 `python-docx`、`PIL` 对应 `Pillow`。扫描器会结合当前环境的元数据和少量常见映射，但无法覆盖所有包；生成 requirements 后应自行查询、核对并替换错误包名，再进行标准打包。项目内由 Cython 等工具生成的普通或带 ABI 标签的 `.pyd`（例如 `tool.pyd`、`tool.cp311-win_amd64.pyd`）会作为本地模块处理，不会写入 requirements；`.pyd` 的 Python ABI 和 32/64 位仍须与实际打包环境一致。

## 系统 Python 启动器

系统 Python 启动器生成依赖目标电脑本机 Python 环境的 Windows 单文件 EXE，不内置 Python、pip 或第三方包。运行时固定执行系统 PATH 解析到的 `python.exe`，不会扫描注册表、虚拟环境、Python 安装目录，也不会回退到 `py.exe`。

- `完整项目，内置资源`：将项目源码和资源文件一起放入 EXE，排除构建、输出、缓存和虚拟环境目录。
- `仅源码，资源外置`：只将 `.py`/`.pyw` 放入 EXE；图片、字体、PDF、配置和数据库等资源需要保持原目录结构，与 EXE 放在同一个传输文件夹中。
- `入口包装`：只将所选入口脚本放入 EXE，可以设置图标和控制台。其他模块和资源使用 EXE 旁的原相对位置。若入口在项目子目录，启动器会把对应的外置子目录加入模块搜索路径。

启动顺序如下：

1. 使用系统 `python.exe` 打开 EXE 内的 Python 程序包。
2. 将内置 Python 源码释放到 `%LOCALAPPDATA%\SystemPythonLaunchers` 缓存；该目录不可写时依次退回 `%TEMP%` 和 EXE 所在目录。
3. 直接运行项目入口，不预先检查 Python 版本、pip 或第三方依赖。
4. 缺少模块或环境不兼容时，由系统 Python 正常抛出错误；窗口模式显示 traceback，控制台模式直接输出。

完整项目模式会收集项目文件，但排除 `build`、`dist`、`.uv-packager`、`.tmp` 等工作目录及同名历史输出 EXE；仅源码模式只收集 `.py` 和 `.pyw`。启动时，完整项目模式的 `sys._MEIPASS` 指向内置项目的释放目录；仅源码模式的 `sys._MEIPASS` 指向 EXE 所在目录，并将入口脚本及本地模块的 `__file__` 映射到 EXE 旁的原项目结构。因而 `Path(__file__).parent / "资源文件"` 会从 EXE 所在目录读取外置资源，不会暴露源码释放缓存目录。环境变量 `SYSTEM_PYTHON_LAUNCHER_DIR` 始终指向 EXE 所在目录。生成完成后还会校验 `__launcher__/config.json`，确认结果确实是系统 Python 启动器。

系统 Python 启动器完全忽略 requirements。“隐藏导入”“排除模块”“PyInstaller 附加参数”和打包预设也只作用于原有 PyInstaller 模式。

## 打包预设

- `标准（推荐）`：常规 PyInstaller 配置。
- `精简优先`：额外排除 IPython、pytest、notebook、sphinx 等开发工具。
- `兼容优先`：禁用 UPX，适合杀毒软件误报或部分二进制库异常的情况。
- `导入调试`：启用 PyInstaller import 调试输出。

“精简优先”可能影响真正依赖上述模块的程序，首次使用后务必运行生成结果。

## 程序图标

- “程序图标”接受文字、表情或 `.ico` 文件路径，支持相对项目目录的路径及带引号的路径。留空使用默认图标。

- 点击“插入表情…”会打开内置表情面板，可按分类选择常见的软件图标、笑脸、人物、动物、食物、符号等表情。
- 未收录的表情可以从浏览器、聊天软件或其他地方复制，再使用 `Ctrl+V` 粘贴到图标文本框。
- 文本图标会自动裁除字体自带的透明留白，再将可见内容放大并保留少量安全边距，无需手工调整图标占比。

图标文本通过 Windows 自带 DirectWrite / Direct2D 和 Python 标准库生成，不需要 Pillow。支持中文、英文、彩色表情及组合表情，输出七种尺寸的透明 ICO。表情按系统 Segoe UI Emoji 字体保留原始颜色，普通文字使用深色。

## 单文件与相对路径

PyInstaller 的单文件程序启动时会解压到 `%TEMP%\_MEIxxxx`。不过，`open("config.json")` 这类相对路径实际取决于当前工作目录，并不会自动指向 EXE 或 `_MEIPASS`。

程序的工作目录由启动方决定，资源与配置路径由项目代码管理。

```python
import sys
from pathlib import Path

APP_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
```

将配置、数据库、日志放在 `APP_DIR`；将通过 `--add-data` 打包的只读资源放在 `BUNDLE_DIR`。`--runtime-tmpdir` 只改变解压位置，不适合作为相对路径问题的通用修复。

## 附加参数

高级选项中每行填写一个完整 PyInstaller 参数。带值参数建议使用等号形式，例如：

```text
--add-data=C:\project\assets;assets
--collect-data=my_package
--hidden-import=my_plugin
```

“自动收集已知包资源”默认开启。检测到依赖文件包含 `ttkbootstrap` 时，工具会自动添加 `--collect-data ttkbootstrap`，避免启动时找不到 `assets/icons/bootstrap.ttf`。如果某个第三方包也缺少非代码资源，可以在附加参数中填写 `--collect-data=包名`。

## 下载、输出与缓存

- 最终结果：项目的 `dist` 目录，或界面中指定的输出目录。
- PyInstaller 工作文件：项目的 `.uv-packager` 目录。
- 系统 Python 启动器工作文件：项目的 `.tmp\uv-packager` 目录；默认在成功后删除，取消勾选缓存清理时才会保留。
- “完成后删除工作缓存”默认勾选，仅在打包成功时删除对应工作目录；输出位于缓存目录内或路径不安全时会拒绝删除。
- GUI 设置：工具目录内的 `settings.json`。首次兼容读取旧 `%APPDATA%\UvPackagerGUI\settings.json`；从其他工作目录启动仍使用工具目录配置。
- 项目打包设置保存在工具目录下的 `项目打包配置` 文件夹。每个项目按解析后的绝对路径对应一个 JSON 文件。GUI 和 CLI 默认从这个文件夹读取配置。全局设置只记录窗口尺寸和最后打开的项目；首次打开没有配置文件的新项目时使用默认值。
- 缓存位置由 uv 自身配置决定，Windows 上默认是 `%LOCALAPPDATA%\uv\cache`。打包页 uv 旁的文件夹图标可打开当前缓存，`doctor --json` 可查看路径。
- 两种独立打包均使用 `uv tool run --isolated`。默认复用本机 Python 解释器，由 uv 在隔离环境中准备 PyInstaller 和项目依赖。
- 各项目共享 uv 缓存。打包工具先离线查找单个镜像的缓存，再组合多个镜像查找可用的包。只有离线无法完成构建时，才按原镜像顺序尝试联网。项目的工作目录清理仅影响构建中间文件。
- 图形界面统一使用打包器默认的 PyInstaller 版本。CLI 可显式指定版本。

1.2.0 起启用 Windows 原生证书，并在当前镜像出现 TLS、连接、DNS 或超时错误时依次尝试其他镜像；无需手动修改后重新打包。

1.2.1 起默认让清华、阿里云和腾讯云镜像绕过本地代理。该设置只针对当前镜像域名，不会影响 uv 从 GitHub 等其他地址下载 Python；可以在“项目与打包”页取消勾选。

1.3.0 起增加“相对路径基准”，可自动将单文件程序的工作目录切换到 EXE 目录或临时资源目录。

1.3.1 起自动收集 `ttkbootstrap` 的字体和图标资源，修复单文件程序启动时缺少 `bootstrap.ttf` 的问题。

1.3.2 起提高默认窗口高度，并自动保存、恢复上次调整后的窗口尺寸，确保镜像源和代理选项无需手动拉伸即可显示。

1.3.3 起移除界面顶部重复的大标题和环境说明，使项目选项占用更多可视空间。

1.4.0 起窗口改用 📦 图标，并支持把 emoji 或短文本自动生成为打包程序的多尺寸 `.ico` 图标。

1.4.1 起自动裁除文本图标的透明留白，并将可见内容放大到合适尺寸，避免桌面图标比其他程序小一圈。

1.4.2 起图标文本框改用 emoji 字体并接管剪贴板粘贴，修复部分新 emoji 无法输入或看起来像空白的问题。

1.4.3 曾尝试在 Tk 窗口中嵌入原生 `EDIT` 输入控件，但部分系统上会被 Tk 重绘层遮挡。

1.4.4 起恢复稳定的普通输入框，并提供独立“系统输入…”窗口；该窗口使用 Windows Forms 原生文本框，可以直接通过 `Win + .` 输入表情。

1.5.0 起移除图标文本旁的“粘贴”和“示例”按钮，并支持把项目文件夹直接拖入主窗口自动识别入口和输出路径。

1.6.0 起使用内置的分类表情面板作为兼容性退化方案，点击表情即可填入；其他表情继续支持从外部复制粘贴。

1.6.1 起将软件图标和常用表情合并为单一表情库，继续保留系统、文件、媒体、工具、笑脸、人物、动物、食物和符号等分类。

1.6.2 起进一步提高默认窗口高度，升级时忽略旧版偏小的窗口尺寸；默认图标文本恢复为 📦，表情面板默认打开“文件与编辑”分类。

1.7.0 起增加“系统 Python 启动器”单文件模式：只调用 PATH 中的 `python.exe`，不限制 Python/依赖版本，缺少 pip 或依赖时提示安装；同时修正启动批处理的源码入口为 `main.py`。

1.7.1 起改为按项目保存打包参数，切换到新项目时恢复默认设置；系统 Python 启动器会排除同名历史 EXE并执行产物类型校验，避免把旧标准 EXE再次打入新程序。

1.7.2 起取消系统 Python 启动器的 pip/依赖预检查，直接交给系统 Python 运行并报告真实错误；依赖界面增加 import 名与 pip 包名可能不同的核对提示。

1.7.3 起将拖放范围限定到对应输入框：项目目录框接收文件夹，入口文件框接收单个 `.py` 文件并自动识别其所在目录；无效路径、错误类型和多项拖放只提示，不再影响程序运行。

1.7.4 起将“保持原样”设为新项目的默认相对路径模式；拖放改为由主窗口安全接收后按落点分发，避免直接挂接输入控件导致卡死，并且拖入入口脚本时不再递归扫描整个目录。

1.7.5 起新项目不再预设打包图标；本地依赖扫描改为从入口文件递归跟踪实际导入的本地模块，不再扫描项目目录中的所有 Python 文件；系统 Python 启动器模式下禁用“一键生成依赖”。

1.7.6 起在软件底部明确提示打包前应将项目放入独立、干净的文件夹，避免直接选择桌面或混有其他项目、无关脚本和多余文件的目录。

1.7.7 起增加按项目保存且默认勾选的“完成后删除工作缓存”选项：PyInstaller 模式删除 `.uv-packager`，系统 Python 启动器模式删除 `.tmp\uv-packager`，并保护位于缓存中的输出结果不被误删；同时提高最小窗口高度，系统启动器模式下自动置灰不生效的 PyInstaller/uv 专属选项，并跳过无意义的 uv 检查。

1.7.8 起系统 Python 启动器分为“完整项目，内置资源”和“仅源码，资源外置”两种输出形式；旧版系统启动器选项自动迁移到完整项目模式，外置资源模式下的 `sys._MEIPASS` 指向 EXE 所在目录。

1.7.9 起修复“仅源码，资源外置”启动器的路径映射：入口脚本和本地模块的 `__file__` 统一指向 EXE 旁的原项目结构，不再变成源码释放缓存目录加相对路径。

1.7.10 起依赖扫描会识别入口目录或项目根目录中的本地 `.pyd` 扩展模块（含 ABI 标签文件名和编译后的包 `__init__`），不再将同名模块误写为 PyPI 依赖；二进制模块不会交给 AST 当源码解析。

1.7.11 起支持 `src` 布局等“运行时修改 sys.path”的项目：依赖扫描会识别入口通过 `sys.path.insert/append` 或 `site.addsitedir` 加入的项目目录（以及约定的 `src` 目录），继续跟踪其中的本地模块；PyInstaller 打包时自动为这些目录追加 `--paths`，并在勾选“自动收集资源”时把目录中的资源文件按原相对位置放进程序包。写在 `except ImportError` 中的备用导入不再写入依赖；选中手写的 `requirements.txt` 时，扫描结果改写到 `runtime-requirements.txt`，不再覆盖原文件。

## 环境要求

- Windows 10/11
- Python 3.10 或更高版本，且包含 Tkinter
- 首次安装工具和依赖时需要网络

### 启动器资源外置

选择“Python 启动器 · 资源外置”（CLI `--mode source`）后，打包器只发布 EXE，内含项目的 `.py` 和 `.pyw`。将 EXE 放到现有资源目录即可使用，入口和本地模块的 `__file__` 仍按 EXE 所在位置映射。
