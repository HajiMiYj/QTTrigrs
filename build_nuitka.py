"""
用 Nuitka 把 QTTrigrs 打包成独立可执行程序（目标：**尽量小**）。

用法::

    python build_nuitka.py                # 默认 standalone（一个文件夹，推荐）
    python build_nuitka.py --onefile      # 打成单个 .exe（更小更好发，启动稍慢）
    python build_nuitka.py --clean        # 先清掉上次的产物
    python build_nuitka.py --console      # 保留控制台窗口，方便看报错
    python build_nuitka.py --jobs 8       # 指定并行编译进程数

产物::

    dist/QTTrigrs.dist/QTTrigrs.exe       （standalone）
    dist/QTTrigrs.exe                     （onefile）

环境要求
--------
* Python 3.12（与两个 Fortran 内核的 cp312 ABI 一致）
* ``pip install nuitka``
* 一个 C 编译器：MSVC，或 MinGW-w64（脚本在找不到 ``cl.exe`` 时会自动加 ``--mingw64``）

体积是怎么压下去的
------------------
* ``--windows-console-mode=disable`` 不生成控制台窗口；
* ``--noinclude-qt-translations`` 不带 Qt 翻译（省好几 MB）；
* ``--noinclude-qt-plugins=…`` 只留真正用到的 Qt 插件；
* ``--noinclude-dlls=opengl32sw.dll`` 去掉 20 MB 级的软件 OpenGL 回退库；
* ``--nofollow-import-to=…`` 不跟随打包运行时用不到的标准库/三方库；
* ``--remove-output`` 打包完删掉中间 ``.build`` 目录；
* 产物里不含 ``__pycache__``、``.pyi``、测试与文档。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENTRY = ROOT / "main.py"
ICON = ROOT / "resources" / "icons" / "app.ico"
LIB_DIR = ROOT / "lib"
DIST_DIR = ROOT / "dist"
APP_NAME = "QTTrigrs"

#: gfortran 运行时 DLL —— 两个 f2py 内核都靠它，必须随包发布
RUNTIME_DLLS = (
    "libgfortran-5.dll",
    "libquadmath-0.dll",
    "libgcc_s_seh-1.dll",
    "libmcfgthread-2.dll",
    "libwinpthread-1.dll",
)

#: 运行时用不到、不跟随打包的库（体积优化；如误删导致报错，把它从列表里去掉即可）
NOFOLLOW_IMPORTS = (
    # —— GUI 无关的常用库 ——
    "tkinter",
    "unittest",
    "unittest2",
    "doctest",
    "pydoc",
    "pytest",
    "_pytest",
    "nose",
    "IPython",
    "jupyter",
    "notebook",
    "nbformat",
    "nbconvert",
    "ipykernel",
    "matplotlib",
    "pandas",
    "seaborn",
    "plotly",
    "lib2to3",
    # —— 打包/安装工具 ——
    "pip",
    "wheel",
    "ensurepip",
    "venv",
    "virtualenv",
    # —— 调试/分析工具 ——
    "curses",
    "pdb",
    "bdb",
    "cProfile",
    "profile",
    "timeit",
    "trace",
    "tracemalloc",
    "faulthandler",
    "pydevd",
)

#: 不打包的 Qt 插件（本程序只用 PNG/ICO 图标与平台插件）
NOINCLUDE_QT_PLUGINS = ",".join((
    "sqldrivers",        # 不用数据库
    "printsupport",      # 不用打印
    "designer",          # 不是 Qt Designer
    "help",              # 不用 Qt Help
    "multimedia",        # 不用音视频
    "webview",
    "webengine",
    "sensors",
    "positioning",
    "location",
    "serialport",
    "texttospeech",
    "virtualkeyboard",
    "gamepads",
    "canbus",
    "scxml",
    "remoteobjects",
    "assetimporters",
))

#: 不打包的 DLL（都很大且本程序用不到）
NOINCLUDE_DLLS = ",".join((
    "opengl32sw.dll",        # 软件 OpenGL 回退，约 20 MB
    "d3dcompiler_47.dll",
    "Qt5WebEngine*.dll",
))


def _log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def _check(onefile: bool) -> None:
    if not ENTRY.is_file():
        raise SystemExit(f"找不到入口文件：{ENTRY}")
    try:
        import nuitka  # noqa: F401
    except ImportError:
        raise SystemExit("未安装 Nuitka。请先执行：\n"
                         f"  {sys.executable} -m pip install nuitka")
    missing = [n for n in RUNTIME_DLLS if not (LIB_DIR / n).is_file()]
    if missing:
        raise SystemExit("lib/ 下缺少 gfortran 运行时 DLL：" + ", ".join(missing) +
                         "\n请先重新编译内核（见 README 第 13 节）或手工补上。")
    if not ICON.is_file():
        _log(f"提示：找不到图标 {ICON.name}，本次不设置程序图标。")


def _clean() -> None:
    for path in (DIST_DIR / f"{APP_NAME}.build",
                 DIST_DIR / f"{APP_NAME}.dist",
                 DIST_DIR / f"{APP_NAME}.onefile-build",
                 ROOT / f"{APP_NAME}.build",
                 ROOT / f"{APP_NAME}.dist",
                 ROOT / f"{APP_NAME}.onefile-build",
                 ROOT / "main.build",
                 ROOT / "main.dist",
                 ROOT / "main.onefile-build"):
        if path.exists():
            _log(f"清理 {path}")
            shutil.rmtree(path, ignore_errors=True)


def _build_command(onefile: bool, console: bool, jobs: int) -> list[str]:
    cmd: list[str] = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyqt5",

        # ---- 体积优化 ----
        "--noinclude-qt-translations",
        f"--noinclude-qt-plugins={NOINCLUDE_QT_PLUGINS}",
        f"--noinclude-dlls={NOINCLUDE_DLLS}",
        f"--nofollow-import-to={','.join(NOFOLLOW_IMPORTS)}",
        "--no-pyi-file",
        "--remove-output",

        # ---- 随包资源 ----
        "--include-data-dir=resources=resources",   # 界面图标
        "--include-data-dir=lib=lib",               # gfortran 运行时

        # ---- 本项目的包（含两个 .pyd 内核）----
        "--include-package=trigrs",
        "--include-package=topoindex",
        "--include-package=ui",

        # ---- 输出 ----
        "--output-dir=dist",
        "--output-filename=" + (f"{APP_NAME}.exe" if onefile else f"{APP_NAME}.exe"),
        "--company-name=QTTrigrs",
        "--product-name=QTTrigrs",
        "--file-version=1.0.0.0",
        "--product-version=1.0.0",
    ]

    if onefile:
        cmd.append("--onefile")
    if not console:
        cmd.append("--windows-console-mode=disable")
    else:
        cmd.append("--windows-console-mode=force")
    if ICON.is_file():
        cmd.append(f"--windows-icon-from-ico={ICON}")
    if jobs > 0:
        cmd.append(f"--jobs={jobs}")
    # 没有 MSVC 时用 MinGW64（脚本会连带下载/复用 MinGW）
    if os.name == "nt" and shutil.which("cl") is None:
        cmd.append("--mingw64")

    cmd.append(str(ENTRY))
    return cmd


def _place_runtime_dlls(dist: Path) -> None:
    """把 gfortran 运行时 DLL 放到 exe 旁边（Windows 一定会搜 exe 所在目录）。"""
    copied = 0
    for name in RUNTIME_DLLS:
        src = LIB_DIR / name
        if src.is_file():
            shutil.copy2(src, dist / name)
            copied += 1
    _log(f"运行时 DLL 已放到 exe 旁：{copied} 个")


def _dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="用 Nuitka 打包 QTTrigrs")
    parser.add_argument("--onefile", action="store_true", help="打成单个 exe")
    parser.add_argument("--clean", action="store_true", help="先清理上次产物")
    parser.add_argument("--console", action="store_true", help="保留控制台窗口（调试用）")
    parser.add_argument("--jobs", type=int, default=0, help="并行编译进程数，0=交给 Nuitka")
    args = parser.parse_args()

    if args.clean:
        _clean()
    _check(args.onefile)

    cmd = _build_command(args.onefile, args.console, args.jobs)
    _log("执行：" + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    t0 = time.time()
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        _log(f"Nuitka 构建失败，退出码 {result.returncode}")
        return result.returncode

    # ---- 后处理 ----
    dist = DIST_DIR / f"{APP_NAME}.dist"
    exe = DIST_DIR / f"{APP_NAME}.exe"
    if args.onefile:
        if exe.is_file():
            _log(f"完成：{exe}（{exe.stat().st_size / 1024 / 1024:.1f} MB，"
                 f"耗时 {time.time() - t0:.0f} s）")
        else:
            _log("未找到 onefile 产物，请检查上面的 Nuitka 输出。")
            return 1
    else:
        if not dist.is_dir():
            _log(f"未找到 standalone 目录：{dist}")
            return 1
        _place_runtime_dlls(dist)
        size = _dir_size(dist)
        _log(f"完成：{dist}")
        _log(f"      {size / 1024 / 1024:.1f} MB，耗时 {time.time() - t0:.0f} s")
        _log(f"      双击运行 {dist / (APP_NAME + '.exe')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
