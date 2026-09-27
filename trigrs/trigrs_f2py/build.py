"""Build the Fortran(f2py) TRIGRS mechanics kernel for the active Python/NumPy ABI.

    python build.py            # 构建并自检
    python build.py --no-test  # 只构建

约定
----
* Fortran 源按官方 TRIGRS 文件结构拆分，放在 ``src/``，每个文件命名
  ``xxx_f2py.<扩展名>``（如 ``savage_f2py.f95``、``flux_f2py.f90``、
  ``calerf_f2py.f``）。
* 构建产物 ``_trigrs_native*.pyd`` 复制到本包目录 ``trigrs_f2py/``；
  gfortran 运行时 DLL 复制到项目根 ``lib/``（与 TopoIndex 共用）。
* 需要 PATH 中有 MinGW-w64 的 ``gcc`` / ``gfortran``，以及 ``numpy`` 的 f2py
  后端（``meson`` + ``ninja``）。
* 目标 ABI 与仓库其它扩展一致：cp312（用 ``python312`` conda 环境或 OSGeo4W）。
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
# gfortran 运行时统一放到项目根目录 lib/（与 TopoIndex 共用一份）
LIB_DIR = PKG_DIR.parents[2] / "lib"
RUNTIME_DLLS = ("libquadmath-0.dll", "libwinpthread-1.dll", "libgcc_s_seh-1.dll",
                "libgfortran-5.dll", "libmcfgthread-2.dll")

# Fortran 源文件（模块在前，含 f2py 入口的驱动最后）
SRC_FILES = [
    "grids_f2py.f95", "input_vars_f2py.f95", "model_vars_f2py.f95",
    "calerf_f2py.f", "derfc_f2py.f", "dbsct_f2py.f", "roots_f2py.f",
    "dsimps_f2py.f95", "dzero_brac_f2py.f90", "smallt_f2py.f95",
    "steady_f2py.f95", "rnoff_f2py.f95",
    "flux_f2py.f90", "ivestp_f2py.f95", "pstpi_f2py.f95", "pstpf_f2py.f95",
    "unsth_f2py.f95", "svgstp_f2py.f95",
    "savage_f2py.f95", "iverson_f2py.f95", "satinf_f2py.f95", "satfin_f2py.f95",
    "unsinf_f2py.f95", "unsfin_f2py.f95",
    "trigrs_f2py.f90",
]
DRIVER = SRC_DIR / "trigrs_f2py.f90"


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
        try:
            subprocess.run([sys.executable, "-m", "mesonbuild.mesonmain", "--version"],
                           check=True, capture_output=True, env=env)
        except Exception:
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
    pyf = PKG_DIR / "_trigrs_native.pyf"
    src_paths = [str(SRC_DIR / f) for f in SRC_FILES]

    print(f"[1/4] 生成 f2py 签名 {pyf.name}")
    subprocess.run(
        [sys.executable, "-m", "numpy.f2py", "-h", str(pyf), str(DRIVER),
         "-m", "_trigrs_native", "--overwrite-signature"],
        cwd=PKG_DIR, env=env, check=True)
    print(f"[2/4] f2py + meson 构建（工作目录 {BUILD_DIR}）")
    subprocess.run(
        [sys.executable, "-m", "numpy.f2py", "-c", str(pyf), *src_paths,
         "-m", "_trigrs_native", "--backend", "meson"],
        cwd=BUILD_DIR, env=env, check=True)

    suffix = sysconfig.get_config_var("EXT_SUFFIX")
    products = list(BUILD_DIR.rglob("_trigrs_native*" + suffix))
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

    print("[4/4] 校验")
    subprocess.run([sys.executable, "-c",
                    "from trigrs_f2py import kernels; print('内核已载入:', "
                    "len([n for n in dir(kernels) if not n.startswith('_')]), '个过程')"],
                   cwd=str(PKG_DIR.parent), check=True)
    print("完成。内核目录：", PKG_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
