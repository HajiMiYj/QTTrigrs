"""
TopoIndex 初始化文件 (tpx_in.txt) 的生成与校验。

TopoIndex 的输入格式与 TRIGRS 一样是“说明行 + 值行”交替的固定行序。
解析由 Fortran 扩展 ``topo_in_read`` 完成，本模块的行序已用
``topoindex.topo_in_read`` 逐项回读验证过（istatus == 0）。

``topoindex.py`` 中的解包顺序为::

    title, heading, aif, pwr, itmax, op[6], lspars, suffix, folder, demfil, dirfil

文件行序：

    1  说明行：TopoIndex Python adaptation; project heading
    2  heading 的值
    3  说明行：Flow-direction numbering scheme (ESRI=1, TopoIndex=2)
    4  aif                      1 = ESRI D8, 2 = TopoIndex 1-9
    5  说明行：Exponent, Number of iterations
    6  pwr, itmax
    7  说明行：Name of elevation grid file
    8  demfil
    9  说明行：Name of direction grid
    10 dirfil
    11 说明行：Save listing of D8 downslope neighbor cells? T/F
    12 op[0]                    是否输出 D8 下游邻居单元列表
    13 说明行：Save grid of D8 downslope neighbor cells? T/F
    14 op[1]                    是否输出 D8 下游邻居单元栅格
    15 说明行：Save cell index number grid? T/F
    16 op[2]                    是否输出单元计算顺序栅格
    17 说明行：Save list of cell number and corresponding index number? T/F
    18 op[3]                    是否输出单元编号与索引号列表
    19 说明行：Save remapped flow-direction grid? T/F
    20 op[4]                    是否输出重编码后的流向栅格
    21 说明行：Save ridge-crest grid? T/F; Sparse (T) or dense (F)?
    22 op[5], lspars            是否输出山脊栅格，以及稀疏(第2个值为 T)或密集
    23 说明行：ID code for output files? (8 characters or less)
    24 suffix

关于输出目录：``topo_in_read`` 返回的 ``folder`` 恒等于 **DEM 所在目录**，
不接受自行指定。``topoindex.py`` 会把它与 ``tpx_in.txt`` 所在目录拼接，
因此输出文件始终写在 DEM 旁边。界面据此把“输出文件夹”做成只读派生值。
"""
from __future__ import annotations

import locale
import os
from dataclasses import dataclass
from pathlib import Path

# 官方固定说明行（与 Fortran 回显一致，不要随意改动）
L_HEADING = "TopoIndex Python adaptation; project heading"
L_AIF = "Flow-direction numbering scheme (ESRI=1, TopoIndex=2)"
L_PWR = "Exponent, Number of iterations"
L_DEM = "Name of elevation grid file"
L_DIR = "Name of direction grid"
L_OP0 = "Save listing of D8 downslope neighbor cells? T/F"
L_OP1 = "Save grid of D8 downslope neighbor cells? T/F"
L_OP2 = "Save cell index number grid? T/F"
L_OP3 = "Save list of cell number and corresponding index number? T/F"
L_OP4 = "Save remapped flow-direction grid? T/F"
L_OP5 = "Save ridge-crest grid? T/F; Sparse (T) or dense (F)?"
L_OUT = "ID code for output files? (8 characters or less)"

MAX_SUFFIX = 8  # Fortran 接口为 character(len=8)

#: 工程附加信息（图层绑定）的注释块标题。
#: 以 "#" 开头，官方程序会忽略；本模块读回时用它恢复图层选择。
ANNOTATION_HEADER = "# --- TopoIndex 工程附加信息（官方程序会忽略本段）---"
ANNOTATION_FOOTER = "# --- 附加信息结束 ---"


def parse_annotations(text: str) -> dict[str, str]:
    """读取输入文件末尾注释块里的 ``key = value`` 附加信息。"""
    info: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        body = stripped.lstrip("#").strip()
        if body.startswith("---") or "=" not in body:
            continue
        key, _, value = body.partition("=")
        key = key.strip()
        value = value.strip()
        if key:
            info[key] = value
    return info


def append_annotations(text: str, info: dict[str, str]) -> str:
    """把附加信息以注释块形式追加到输入文件末尾。"""
    if not info:
        return text
    lines = [text.rstrip("\n"), "", ANNOTATION_HEADER]
    for key in sorted(info):
        lines.append(f"# {key} = {info[key]}")
    lines.append(ANNOTATION_FOOTER)
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Fortran 接口的路径编码
# --------------------------------------------------------------------------
# Windows 上 Fortran 运行时用“系统 ANSI 代码页”打开文件，而 f2py 在把
# Python str 转成 C 字符串时用的是默认编码，遇到中文路径会抛
# UnicodeEncodeError，并被包装成极具误导性的
# “function takes exactly 5 arguments (1 given)”。
# 传 bytes 可以绕开这段转换，因此所有交给 Fortran 的路径都走
# :func:`fortran_path`。
def _ansi_codec() -> str:
    """
    返回 Windows 的 ANSI 代码页名称。

    这一步很关键，而且不能用 ``locale.getpreferredencoding()``：它的取值随
    启动方式而变（QGIS 启动器下可能是 UTF-8），而 Fortran 运行时始终用
    **ANSI 代码页** 打开文件。用 ``GetACP`` 拿到的是确定的系统 ANSI 代码页
    （中文系统通常 936），只有它才能让 Fortran 找到中文路径。
    """
    try:
        import ctypes

        acp = int(ctypes.windll.kernel32.GetACP())
        if acp > 0:
            return f"cp{acp}"
    except Exception:
        pass
    return "mbcs"


def _preferred_codecs() -> list[str]:
    """按可靠性排序的候选编码：先 ANSI 代码页，再 mbcs，最后 UTF-8。"""
    codecs: list[str] = []
    for name in (_ansi_codec(), "mbcs", "utf-8"):
        if name and name.lower() not in {c.lower() for c in codecs}:
            codecs.append(name)
    return codecs


def fortran_path(path: str | os.PathLike) -> bytes:
    """
    把路径转成 Fortran 运行时能够打开的字节串。

    优先使用系统 ANSI 代码页（Windows 上 Fortran 的 ``open`` 用的就是它），
    失败时退回文件系统编码。
    """
    text = str(path)
    for codec in _preferred_codecs():
        try:
            return text.encode(codec)
        except (UnicodeEncodeError, LookupError):
            continue
    return os.fsencode(text)


def from_fortran_text(value) -> str:
    """
    把 Fortran 返回的字符内容解码成 :class:`str`。

    实测（cp936 中文 Windows，numpy.f2py 生成的扩展）：入参与回传的编码
    **并不对称**——

    * 传给 Fortran 的 ``bytes`` 会被原样落到 Fortran 字符数组里，Fortran 用
      系统 ANSI 代码页打开文件，所以入参要用 :func:`fortran_path`；
    * Fortran 返回的字符数组，f2py 是按 **UTF-8** 还原成 Python ``bytes`` 的
      （numpy 的 ``str_`` 约定），所以回传值应当按 UTF-8 解码。

    这里先试 UTF-8，再退回 ANSI 代码页，两种情况都能处理。
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    raw = bytes(value)
    for codec in ("utf-8", *_preferred_codecs()):
        try:
            return raw.decode(codec)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "replace")


class TopoIndexInputError(ValueError):
    """TopoIndex 参数不完整或不合法时抛出。"""


@dataclass
class TopoIndexInput:
    """界面上 TopoIndex 全部参数的结构化表示。"""

    title: str = "TopoIndex"
    heading: str = "TopoIndex project"
    aif: int = 1                      # 1 = ESRI D8, 2 = TopoIndex 1-9
    pwr: float = -1.0                 # 坡度指数
    itmax: int = 10                   # 计算顺序修正的最大迭代次数
    demfil: str = ""                  # DEM 高程栅格
    dirfil: str = ""                  # 流向栅格（可留空）
    save_list_downslope: bool = True
    save_grid_downslope: bool = True
    save_grid_index: bool = True
    save_list_index: bool = True
    save_grid_direction: bool = True
    save_grid_ridge: bool = False
    ridge_sparse: bool = False
    suffix: str = ""                  # 输出标识，最长 8 字符

    @property
    def output_folder(self) -> str:
        """输出目录：由 DEM 所在目录决定（TopoIndex 固定行为）。"""
        if not str(self.demfil).strip():
            return ""
        return str(Path(str(self.demfil)).resolve().parent)


def _tf(value: bool) -> str:
    return "T" if value else "F"


def _num(value: float) -> str:
    if isinstance(value, int):
        return str(value)
    f = float(value)
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return repr(f)


def build_tpx_in(data: TopoIndexInput) -> str:
    """把 :class:`TopoIndexInput` 渲染成 tpx_in.txt 的完整文本。"""
    if data.aif not in (1, 2):
        raise TopoIndexInputError("流向编码方案只能是 1 (ESRI D8) 或 2 (TopoIndex 1-9)")
    if data.itmax < 1:
        raise TopoIndexInputError("itmax 必须大于等于 1")
    if len(data.suffix) > MAX_SUFFIX:
        raise TopoIndexInputError(f"suffix 最长 {MAX_SUFFIX} 个字符（Fortran 接口限制）")

    lines = [
        L_HEADING,
        data.heading.strip() or "TopoIndex project",
        L_AIF,
        str(int(data.aif)),
        L_PWR,
        f"{_num(data.pwr)}, {int(data.itmax)}",
        L_DEM,
        data.demfil,
        L_DIR,
        data.dirfil,
        L_OP0,
        _tf(data.save_list_downslope),
        L_OP1,
        _tf(data.save_grid_downslope),
        L_OP2,
        _tf(data.save_grid_index),
        L_OP3,
        _tf(data.save_list_index),
        L_OP4,
        _tf(data.save_grid_direction),
        L_OP5,
        f"{_tf(data.save_grid_ridge)},{_tf(data.ridge_sparse)}",
        L_OUT,
        data.suffix,
    ]
    return "\n".join(lines) + "\n"


def write_tpx_in(data: TopoIndexInput, path: str | os.PathLike) -> Path:
    """写出 tpx_in.txt，返回实际写入的路径。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_tpx_in(data), encoding="utf-8", newline="\n")
    return target


def looks_like_tpx_in(path: str | os.PathLike) -> bool:
    """判断文件是否为 TopoIndex 输入文件（用首行说明行识别）。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.strip():
                    return line.strip().startswith("TopoIndex")
    except OSError:
        return False
    return False


def parse_tpx_in(path: str | os.PathLike) -> TopoIndexInput:
    """
    解析官方 tpx_in.txt，返回 :class:`TopoIndexInput`。

    文件是“说明行 + 值行”交替的固定行序，这里严格按对读取，顺序与
    :func:`build_tpx_in` 的写出顺序一一对应。末尾的 ``#`` 注释块（本模块
    写入的图层绑定）会被自动忽略。
    """
    lines = [
        line.split("#", 1)[0].strip()
        for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        if not line.strip().startswith("#")
    ]
    # 至少要能放下 12 对“说明行 + 值行”
    if len(lines) < 24:
        raise TopoIndexInputError("文件内容过少，不像是一个 tpx_in.txt")

    # pairs[i] 是第 i 个值行（0 基），说明行位于 2*i
    pairs = [lines[2 * i + 1] for i in range(12)]

    heading = pairs[0]
    aif = int(float(pairs[1] or 1))

    exponent = [p for p in pairs[2].replace(",", " ").split() if p]
    pwr = float(exponent[0]) if exponent else -1.0
    itmax = int(float(exponent[1])) if len(exponent) > 1 else 10

    demfil = pairs[3]
    dirfil = pairs[4]

    def flag(token: str) -> bool:
        return str(token).strip().upper().startswith("T")

    ridge = [p.strip() for p in pairs[10].split(",")]

    return TopoIndexInput(
        title=heading or "TopoIndex",
        heading=heading or "TopoIndex project",
        aif=aif if aif in (1, 2) else 1,
        pwr=pwr,
        itmax=max(1, itmax),
        demfil=demfil,
        dirfil=dirfil,
        save_list_downslope=flag(pairs[5]),
        save_grid_downslope=flag(pairs[6]),
        save_grid_index=flag(pairs[7]),
        save_list_index=flag(pairs[8]),
        save_grid_direction=flag(pairs[9]),
        save_grid_ridge=bool(ridge) and flag(ridge[0]),
        ridge_sparse=len(ridge) > 1 and flag(ridge[1]),
        suffix=pairs[11][:MAX_SUFFIX],
    )


def validate(data: TopoIndexInput) -> tuple[list[str], list[str]]:
    """
    检查参数。

    :return: ``(errors, warnings)``；``errors`` 才会阻止运行。
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        build_tpx_in(data)
    except TopoIndexInputError as exc:
        return [str(exc)], warnings

    if not str(data.demfil).strip():
        errors.append("未指定 DEM 高程栅格")
    elif not Path(str(data.demfil)).exists():
        errors.append(f"DEM 高程栅格不存在：{data.demfil}")

    if str(data.dirfil).strip() and not Path(str(data.dirfil)).exists():
        errors.append(f"流向栅格不存在：{data.dirfil}")
    elif not str(data.dirfil).strip():
        warnings.append("未指定流向栅格：TopoIndex 只会输出网格尺寸参数文件")

    if data.pwr < 0 and data.save_grid_ridge:
        errors.append("pwr < 0（D-infinity）时无法计算山脊栅格，请关闭“保存山脊栅格”")

    out_dir = data.output_folder
    if out_dir and not Path(out_dir).is_dir():
        errors.append(f"输出文件夹不存在：{out_dir}")

    return errors, warnings
