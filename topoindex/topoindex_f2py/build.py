"""Build the Fortran(f2py) TopoIndex kernel for the active Python/NumPy ABI.

    python build.py            # 构建并自检
    python build.py --no-test  # 只构建

约定
----
* Fortran 源放在 ``src/``，每个文件命名 ``xxx_f2py.<扩展名>``。
* 构建产物 ``topoindex*.pyd`` 复制到本包目录 ``topoindex_f2py/``；
  gfortran 运行时 DLL 复制到项目根 ``lib/``（与 TRIGRS 共用一份）。
* 需要 PATH 中有 MinGW-w64 的 ``gcc`` / ``gfortran``，以及 ``numpy`` 的 f2py
  后端（``meson`` + ``ninja``）。
* 目标 ABI 与仓库其它扩展一致：cp312（用 ``python312`` conda 环境）。

所有入口都标记了 ``!f2py threadsafe``（无 Python 回调），因此 f2py 生成的
包装器会在调用期间释放 GIL——这是修复 TopoIndex 在后台线程中阻塞主进程
（旧 .pyd 持锁约 30s）的关键。
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig

PKG_DIR = Path(__file__).resolve().parent
SRC_DIR = PKG_DIR / "src"
BUILD_DIR = PKG_DIR / "_workspace" / "build"
# gfortran 运行时统一放到项目根目录 lib/（与 TRIGRS 共用一份）
LIB_DIR = PKG_DIR.parents[1] / "lib"
RUNTIME_DLLS = ("libquadmath-0.dll", "libwinpthread-1.dll", "libgcc_s_seh-1.dll",
                "libgfortran-5.dll", "libmcfgthread-2.dll")

# 全部入口都是顶层 subroutine，逐个编译（顺序无关）。
SRC_FILES = [
    "sindex_f2py.f90",
    "nxtcel_f2py.f90",
    "slofac_f2py.f90",
    "tpindx_f2py.f90",
]
MODULE = "topoindex"


def _check_toolchain(env):
    missing = []
    for tool in ("gfortran", "gcc"):
        if not shutil.which(tool, path=env["PATH"]):
            missing.append(tool)
    if missing:
        raise SystemExit("缺少编译工具：" + ", ".join(missing) +
                         "\n请安装 MinGW-w64（例如 C:\\mingw64）并把 bin 目录加入 PATH。")
    try:
        import mesonbuild  # noqa: F401
    except ImportError:
        raise SystemExit("缺少 f2py 的 Meson 后端。请先执行：\n"
                         f"  {sys.executable} -m pip install meson ninja")
    return shutil.which("gfortran", path=env["PATH"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-test", action="store_true", help="构建后跳过自检")
    args = parser.parse_args()

    env = os.environ.copy()
    scripts = str(Path(sys.executable).parent / "Scripts")
    user_scripts = str(sysconfig.get_path(
        "scripts", scheme="nt_user" if os.name == "nt" else "posix_user"))
    env["PATH"] = os.pathsep.join([scripts, user_scripts, env.get("PATH", "")])

    compiler = _check_toolchain(env)
    env["FC"] = compiler
    env["CC"] = shutil.which("gcc", path=env["PATH"]) or "gcc"
    env["FFLAGS"] = "-O3 -fno-fast-math -ffree-line-length-none -fno-range-check"
    env["LDFLAGS"] = "-static-libgfortran -static-libgcc" if os.name == "nt" else ""

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    pyf = PKG_DIR / "topoindex.pyf"
    src_paths = [str(SRC_DIR / f) for f in SRC_FILES]

    print(f"[1/4] 生成 f2py 签名 {pyf.name}")
    subprocess.run(
        [sys.executable, "-m", "numpy.f2py", "-h", str(pyf), *src_paths,
         "-m", MODULE, "--overwrite-signature"],
        cwd=PKG_DIR, env=env, check=True)
    print(f"[2/4] f2py + meson 构建（工作目录 {BUILD_DIR}）")
    subprocess.run(
        [sys.executable, "-m", "numpy.f2py", "-c", str(pyf), *src_paths,
         "-m", MODULE, "--backend", "meson"],
        cwd=BUILD_DIR, env=env, check=True)

    suffix = sysconfig.get_config_var("EXT_SUFFIX")
    products = list(BUILD_DIR.rglob(MODULE + "*" + suffix))
    if len(products) != 1:
        raise RuntimeError(f"构建未产生唯一的扩展模块，找到 {len(products)} 个")
    print(f"[3/4] 安装 {products[0].name} → {PKG_DIR}")
    shutil.copy2(products[0], PKG_DIR / products[0].name)

    if os.name == "nt":
        LIB_DIR.mkdir(parents=True, exist_ok=True)
        for name in RUNTIME_DLLS:
            source = Path(compiler).parent / name
            if source.exists():
                shutil.copy2(source, LIB_DIR / name)

    if args.no_test:
        print("完成。内核目录：", PKG_DIR)
        return 0

    print("[4/4] 校验")
    subprocess.run([sys.executable, "-c",
                    "from topoindex_f2py import topoindex; "
                    "names=[n for n in dir(topoindex) if not n.startswith('_')]; "
                    "print('内核已载入:', len(names), '个过程:', ', '.join(names))"],
                   cwd=str(PKG_DIR.parent), check=True)
    print("完成。内核目录：", PKG_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
