"""
TRIGRS 力学内核的 Fortran(f2py) 扩展装载器。

``_trigrs_native.cp312-win_amd64.pyd`` 是 f2py 编译的 Fortran 内核，
内部 module ``trigrs_kernels`` 通过 ``trigrs_solve`` 暴露唯一入口。

gfortran 运行时 DLL 统一放在项目根目录的 ``lib/``（与 TopoIndex 共用一份），
本装载器沿目录树逐级向上查找 ``lib/`` 并注册，保证扩展能被正确加载。

用法::

    from .trigrs_f2py import kernels
    kernels.trigrs_solve(...)
"""
from __future__ import annotations

import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent

#: 用于识别 gfortran 运行时目录的 DLL 标记
_RUNTIME_MARKERS = ("libgfortran-5.dll", "libquadmath-0.dll", "libgcc_s_seh-1.dll")
_MAX_LEVELS = 8


def _register_dll_dirs() -> None:
    """沿目录树逐级向上查找 ``lib/``，注册确实含 gfortran 运行时的目录。"""
    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return
    parent = _HERE
    for _ in range(_MAX_LEVELS):
        parent = parent.parent
        if parent == parent.parent:  # 已到根
            break
        lib = parent / "lib"
        if not lib.is_dir():
            continue
        names = {p.name.lower() for p in lib.iterdir() if p.is_file()}
        if all(m in names for m in _RUNTIME_MARKERS):
            try:
                os.add_dll_directory(str(lib))
            except OSError:
                pass


_register_dll_dirs()

try:
    from ._trigrs_native import trigrs_kernels as kernels
except ImportError as exc:  # pragma: no cover - 给出友好提示
    raise ImportError(
        "TRIGRS Fortran 内核未编译或 ABI 不匹配。"
        "请在 Python 3.12 环境（含 numpy/f2py/meson，且 PATH 有 MinGW-w64）下执行：\n"
        f"    python {_HERE / 'build.py'}"
    ) from exc

__all__ = ["kernels"]
