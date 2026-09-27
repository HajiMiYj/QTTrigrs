"""
TopoIndex f2py extension loader.

The pre-compiled ``topoindex.cp312-win_amd64.pyd`` needs the gfortran runtime
DLLs (``libgfortran-5.dll``, ``libquadmath-0.dll``, ``libgcc_s_seh-1.dll``,
``libmcfgthread-2.dll``).

Upstream shipped them in a ``lib/`` folder inside the package; after the module
was folded into the host application that folder may live anywhere above the
package (this project keeps it in the repository root as ``<repo>/lib``).
Hard-coding a fixed number of ``..`` levels is brittle, so instead every
directory on the path from this file up to the filesystem root is inspected for
a ``lib/`` folder -- and a ``lib/`` folder directly containing the runtime is
accepted wherever it sits.

A missing runtime is not fatal: many environments already have gfortran on
``PATH``, so no exception is raised here; the extension import itself reports
the problem if the DLLs really cannot be found.
"""
from __future__ import annotations

import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent

#: DLL file names shipped with the gfortran runtime (used to recognise a lib dir)
_RUNTIME_MARKERS = (
    "libgfortran-5.dll",
    "libquadmath-0.dll",
    "libgcc_s_seh-1.dll",
)

#: how many levels above the package to inspect (repo root is 4 up in this project)
_MAX_LEVELS = 8


def _candidate_lib_dirs() -> list[Path]:
    """
    返回所有可能存放 Fortran 运行时的 ``lib`` 目录。

    先看包内（上游布局），再沿目录树逐级向上找，顺序即优先级。
    """
    candidates: list[Path] = []

    # 1) 包内布局：.../topoindex_f2py/lib 与 .../TopoIndex/lib
    candidates.append(_HERE / "lib")
    candidates.append(_HERE.parent / "lib")

    # 2) 沿目录树向上：.../trigrs/lib、.../physical_model/lib、.../hazard/lib、
    #    <repo>/lib 等等，逐级都试一遍，不依赖具体层数
    parent = _HERE
    for _ in range(_MAX_LEVELS):
        parent = parent.parent
        if parent == parent.parent:  # 已到根
            break
        candidates.append(parent / "lib")

    # 去重且保持顺序
    seen: set[str] = set()
    unique: list[Path] = []
    for path in candidates:
        key = os.path.normcase(str(path))
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _looks_like_runtime_dir(path: Path) -> bool:
    """目录是否存在，且包含 Fortran 运行时 DLL。"""
    try:
        if not path.is_dir():
            return False
        names = {p.name.lower() for p in path.iterdir() if p.is_file()}
    except OSError:
        return False
    return all(marker in names for marker in _RUNTIME_MARKERS)


def _containing_runtime_dir() -> list[Path]:
    """候选目录中确实包含运行时的那些（优先注册它们，避免误加无关目录）。"""
    return [p for p in _candidate_lib_dirs() if _looks_like_runtime_dir(p)]


def _register_dll_dirs() -> list[str]:
    """注册所有可用的运行时目录，返回实际注册成功的目录。"""
    added: list[str] = []
    if not hasattr(os, "add_dll_directory"):
        return added

    # 优先注册确实含运行时的目录；若一个都没找到，则退回注册存在的候选目录
    targets = _containing_runtime_dir() or [p for p in _candidate_lib_dirs() if p.is_dir()]

    for candidate in targets:
        try:
            os.add_dll_directory(str(candidate))
            added.append(str(candidate))
        except OSError:
            continue
    return added


_DLL_DIRS = _register_dll_dirs()

# 同时把运行时目录加到 PATH 前面：某些依赖的解析不走 add_dll_directory，
# 需要 PATH 才能找到（例如扩展自身再间接加载的 DLL）。
for _dir in reversed(_DLL_DIRS):
    _current = os.environ.get("PATH", "")
    if os.path.normcase(_dir) not in os.path.normcase(_current):
        os.environ["PATH"] = _dir + os.pathsep + _current

__all__ = ["topoindex"]
