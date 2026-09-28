"""
用 Nuitka 把 QTTrigrs 打包成独立可执行程序（目标：**尽量小**）。

用法::

    python build_nuitka.py                # 默认 standalone（一个文件夹，体积最小、推荐）
    python build_nuitka.py --onefile      # 单个 .exe（好发，但没法做构建后裁剪，会大 ~16 MB）
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
* C 编译器：优先用已安装的 **MSVC**（脚本用 vswhere 探测，无需 Developer 命令行）；
  没有 MSVC 时才回退 ``--mingw64``（会下载 Nuitka 指定的 MinGW）

体积是怎么压下去的（实测 60 MB → 44 MB）
----------------------------------------
1. ``--noinclude-qt-translations``            不带 Qt 翻译文件；
2. ``--noinclude-qt-plugins=…``               只留真正用到的 Qt 插件；
3. ``--nofollow-import-to=…``                 不跟随打包运行时用不到的库；
4. ``--remove-output``                        打包完删掉中间 ``.build``；
5. **构建后裁剪**（``PRUNE_GLOBS``）：
   Nuitka 的 PyQt5 插件会把 Qt 的 DLL 一股脑塞进产物，而 ``--noinclude-dlls``
   **管不到插件注入的 DLL**（实测无效）。所以打包完成后再按名单删一遍，
   把 QtQuick/Qml、QtNetwork、OpenSSL、多媒体后端、用不到的图片格式插件和
   ``opengl32sw.dll``（20 MB）等清理掉。本小程序实测可省约 16 MB。
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

#: 运行时用不到、不跟随打包的库
NOFOLLOW_IMPORTS = (
    "tkinter", "unittest", "unittest2", "doctest", "pydoc",
    "pytest", "_pytest", "nose",
    "IPython", "jupyter", "notebook", "nbformat", "nbconvert", "ipykernel",
    "matplotlib", "pandas", "seaborn", "plotly",
    "lib2to3",
    "pip", "wheel", "ensurepip", "venv", "virtualenv",
    "curses", "pdb", "bdb", "cProfile", "profile", "timeit", "trace",
    "tracemalloc", "faulthandler", "pydevd",
    # 本项目代码里没有 import scipy（只有 numpy）；带上会白白多几十 MB
    "scipy",
)

#: 不打包的 Qt 插件类别（本程序只用 PNG/ICO 图标与 Windows 平台插件）
NOINCLUDE_QT_PLUGINS = ",".join((
    "sqldrivers", "printsupport", "designer", "help", "multimedia",
    "webview", "webengine", "sensors", "positioning", "location",
    "serialport", "texttospeech", "virtualkeyboard", "gamepads", "canbus",
    "scxml", "remoteobjects", "assetimporters",
))

#: 构建后再删一遍的产物文件（glob，大小写不敏感匹配）。
#: 必须保留的：qt5core / qt5gui / qt5widgets / qwindows / qico / qjpeg / python* / vcruntime* / zlib
PRUNE_GLOBS = (
    # Qt Quick / QML / 3D —— 本程序只用 Widgets
    "qt5quick*.dll", "qt5qml*.dll",
    # 用不到的 Qt 模块
    "qt5network.dll", "qt5multimedia*.dll", "qt5websockets.dll", "qt5svg.dll",
    "qt5dbus.dll", "qt5designer.dll", "qt5xmlpatterns.dll", "qt5location.dll",
    "qt5positioning.dll", "qt5sql.dll", "qt5test.dll", "qt5bluetooth.dll",
    "qt5nfc.dll", "qt5sensors.dll", "qt5serialport.dll", "qt5webengine*.dll",
    "qt5webchannel.dll",
    # OpenSSL（只有 QtNetwork 需要）
    "libeay32.dll", "ssleay32.dll", "libcrypto-*.dll", "libssl-*.dll",
    # 多媒体后端
    "dsengine.dll", "wmfengine.dll", "qtmedia_*.dll",
    # 用不到的图片格式插件（PNG 内建于 Qt5Gui；ICO 保留给窗口图标）
    "qgif.dll", "qicns.dll", "qtga.dll", "qtiff.dll", "qwbmp.dll",
    "qwebp.dll", "qsvg.dll", "qsvgicon.dll",
    # 用不到的平台 / 主题插件
    "qwebgl.dll", "qxdgdesktopportal.dll", "qminimal.dll",
    # 大块头且用不到
    "opengl32sw.dll", "d3dcompiler_47.dll",
)

#: 构建后整目录删掉（Nuitka 会把包目录里的编译工作区一起收进去）
PRUNE_DIRS = ("_workspace",)

#: **可选**：精简 Intel MKL（本机 conda 的 numpy 是 MKL 版，MKL 能占 400+ MB）。
#: 只保留 mkl_rt / core / intel_thread / def / avx2 这套，删掉 avx512、mc3、
#: tbb_thread、以及对应的 vml 变体；实测可省约 160 MB。
#: 风险：删掉的是「按 CPU 分发的内核」，理论上在只支持 AVX-512 的机器上
#: 会退化（不会崩），但**务必在目标机器上实测**。默认不开，用 --prune-mkl 启用。
#: 想彻底解决体积问题，最好的办法是用 pip 装 numpy（OpenBLAS 版，只有几十 MB），
#: 见文件末尾“怎么让包更小”。
MKL_PRUNE_GLOBS = (
    # 按 CPU 分发的内核（保留 avx2 与 def 即可覆盖绝大多数机器）
    "mkl_avx512*.dll",
    "mkl_mc3*.dll",
    "mkl_tbb_thread*.dll",
    "mkl_vml_avx512*.dll",
    "mkl_vml_mc3*.dll",
    "mkl_vml_cmpt*.dll",
    # 分布式 / 集群 BLAS（MPI、ScaLAPACK、BLACS、CDS），numpy 完全用不到
    "mkl_blacs*.dll",
    "mkl_scalapack*.dll",
    "mkl_cdft*.dll",
)


def _log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def _has_msvc() -> bool:
    """是否能用 MSVC：cl 在 PATH 上，或 vswhere 能找到 Visual Studio。"""
    if shutil.which("cl"):
        return True
    if os.name != "nt":
        return False
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    vswhere = Path(pf86) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if not vswhere.is_file():
        return False
    try:
        out = subprocess.run([str(vswhere), "-latest", "-products", "*",
                              "-property", "installationPath"],
                             capture_output=True, text=True, timeout=60)
        return bool(out.stdout.strip())
    except Exception:
        return False


def _check() -> None:
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
                         "\n请重新编译内核（见 README 第 13 节）或手工补上。")
    if not ICON.is_file():
        _log(f"提示：找不到 {ICON.name}，本次不设置程序图标。")


def _dist_dir() -> Path:
    """Nuitka 用**入口模块名**命名产物目录：main.py → dist/main.dist。"""
    exact = DIST_DIR / f"{ENTRY.stem}.dist"
    if exact.is_dir():
        return exact
    found = sorted(p for p in DIST_DIR.glob("*.dist") if p.is_dir())
    return found[0] if found else exact


def _clean() -> None:
    for base in (DIST_DIR, ROOT):
        if not base.is_dir():
            continue
        for pattern in ("*.build", "*.dist", "*.onefile-build"):
            for path in base.glob(pattern):
                if path.is_dir():
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
        f"--nofollow-import-to={','.join(NOFOLLOW_IMPORTS)}",
        "--remove-output",

        # ---- 随包资源 ----
        "--include-data-dir=resources=resources",   # 界面图标
        "--include-data-dir=lib=lib",               # gfortran 运行时

        # ---- 本项目的包（含两个 .pyd 内核）----
        "--include-package=trigrs",
        "--include-package=topoindex",
        "--include-package=ui",

        # ---- 输出与元信息 ----
        "--output-dir=dist",
        f"--output-filename={APP_NAME}.exe",
        "--company-name=QTTrigrs",
        "--product-name=QTTrigrs",
        "--file-version=1.0.0.0",
        "--product-version=1.0.0",
    ]

    if onefile:
        cmd.append("--onefile")
    cmd.append("--windows-console-mode=" + ("force" if console else "disable"))
    if ICON.is_file():
        cmd.append(f"--windows-icon-from-ico={ICON}")
    if jobs > 0:
        cmd.append(f"--jobs={jobs}")

    # 编译器：优先 MSVC；没有才让 Nuitka 用（并下载）它指定的 MinGW64
    if os.name == "nt" and not _has_msvc():
        _log("未检测到 MSVC，改用 --mingw64（首次会下载 MinGW，约 100 MB）")
        cmd.append("--mingw64")

    cmd.append(str(ENTRY))
    return cmd


def _place_runtime_dlls(dist: Path) -> int:
    """把 gfortran 运行时放到 exe 旁边（Windows 一定搜 exe 所在目录）。"""
    copied = 0
    for name in RUNTIME_DLLS:
        src = LIB_DIR / name
        if src.is_file():
            shutil.copy2(src, dist / name)
            copied += 1
    return copied


def _prune(dist: Path, mkl: bool = False) -> tuple[int, int]:
    """
    删除产物里用不到的文件，返回 ``(删除个数, 省下的字节)``。

    :param mkl: 是否一并精简 Intel MKL（见 ``MKL_PRUNE_GLOBS`` 的风险说明）
    """
    removed = 0
    saved = 0

    def _drop(path: Path) -> None:
        nonlocal removed, saved
        if path.is_file():
            saved += path.stat().st_size
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass

    # 先整目录删（Nuitka 会把包目录里的编译工作区也收进来）
    for name in PRUNE_DIRS:
        for path in list(dist.rglob(name)):
            if path.is_dir():
                saved += sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
                shutil.rmtree(path, ignore_errors=True)
                removed += 1

    # 再按文件名删
    patterns = list(PRUNE_GLOBS) + (list(MKL_PRUNE_GLOBS) if mkl else [])
    for pattern in patterns:
        for path in dist.rglob(pattern):
            _drop(path)
    return removed, saved


def _dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="用 Nuitka 打包 QTTrigrs")
    parser.add_argument("--onefile", action="store_true", help="打成单个 exe")
    parser.add_argument("--clean", action="store_true", help="先清理上次产物")
    parser.add_argument("--console", action="store_true", help="保留控制台窗口（调试用）")
    parser.add_argument("--jobs", type=int, default=0, help="并行编译进程数，0=交给 Nuitka")
    parser.add_argument("--no-prune", action="store_true", help="不做构建后裁剪")
    parser.add_argument("--prune-mkl", action="store_true",
                        help="额外精简 Intel MKL（省约 160 MB，需在目标机器实测）")
    args = parser.parse_args()

    if args.clean:
        _clean()
    _check()

    cmd = _build_command(args.onefile, args.console, args.jobs)
    _log("执行：" + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    t0 = time.time()
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        _log(f"Nuitka 构建失败，退出码 {result.returncode}")
        return result.returncode

    exe = DIST_DIR / f"{APP_NAME}.exe"
    dist = _dist_dir()

    if args.onefile:
        if not exe.is_file():
            _log("未找到 onefile 产物，请检查上面的 Nuitka 输出。")
            return 1
        _log(f"完成：{exe}")
        _log(f"      {exe.stat().st_size / 1024 / 1024:.1f} MB，耗时 {time.time() - t0:.0f} s")
        _log("      提示：onefile 无法做构建后裁剪，体积比 standalone 大；"
             "要最小体积请用默认的 standalone。")
        return 0

    if not dist.is_dir():
        _log(f"未找到 standalone 目录（找的是 {dist}）")
        return 1

    before = _dir_size(dist)
    if not args.no_prune:
        removed, saved = _prune(dist, mkl=args.prune_mkl)
        _log(f"构建后裁剪：删除 {removed} 项，省下 {saved / 1024 / 1024:.1f} MB")
    copied = _place_runtime_dlls(dist)
    _log(f"gfortran 运行时已放到 exe 旁：{copied} 个")
    after = _dir_size(dist)

    _log(f"完成：{dist}")
    _log(f"      {before / 1024 / 1024:.1f} MB → {after / 1024 / 1024:.1f} MB，"
         f"耗时 {time.time() - t0:.0f} s")
    _log(f"      双击运行 {dist / (APP_NAME + '.exe')}")
    if after > 300 * 1024 * 1024:
        _log("      体积仍然很大 —— 多半是 numpy 用了 Intel MKL（mkl_*.dll 占 400+ MB）。"
             "用 pip 装的 numpy 是 OpenBLAS 版，包会小得多，见 README 第 14 节。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
