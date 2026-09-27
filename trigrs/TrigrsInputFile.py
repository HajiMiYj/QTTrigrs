"""
TRIGRS 初始化文件 (tr_in.txt) 的生成与校验。

本模块只负责“把界面上的参数翻译成 TRIGRS 官方要求的文本格式”，
不依赖任何界面代码，因此既可以被 GUI 调用，也可以在脚本/批处理中直接用。

文件行序严格对应 USGS TRIGRS v2.1 的 tr_in 读取顺序，参见
``engine/TrigrsSubroutine/TriNi.py`` 中的 ``trini()``：

    1  工程名称                 Name of project
    2  tx, nmax, mmax, zones
    3  nzs, zmin, uww, nper, t
    4  zmax, depth, rizero, Min_Slope_Angle, Max_Slope_Angle
    5  zone i + cohesion..Alpha      （共 zones 组）
    6  cri(1..nper)
    7  capt(1..nper+1)
    8  slofil
    9  elevfil
    10 zonfil
    11 zfil
    12 depfil
    13 rizerofil
    14 rifil(1..nper)            （每期一行）
    15 nxtfil
    16 ndxfil
    17 dscfil
    18 wffil
    19 folder
    20 suffix
    21 rodoc
    22 outp(3) 最小安全系数栅格
    23 outp(4) 最小安全系数深度栅格
    24 outp(5) 最小安全系数处压力水头栅格
    25 outp(1) + el_or_dep        （保存水位栅格）
    26 outp(6) 实际入渗率栅格
    27 outp(7) 非饱和区基底通量栅格
    28 flag, spcg
    29 nout
    30 tsav(1..nout)
    31 lskip
    32 lany
    33 llus
    34 lps0
    35 outp(8) 质量平衡
    36 flowdir
    37 bkgrof
    38 lasc
    39 lpge0
    40 igcapf
    41 deepz, deepwat
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# 官方文本中的说明行（原样保留，便于与 USGS 文档逐行对照）
# --------------------------------------------------------------------------
H = {
    "title": "Name of project (up to 255 characters)",
    "control": "tx, nmax, mmax, zones ",
    "simulation": "nzs,  zmin,  uww,    nper    t",
    "condition": "zmax,   depth,   rizero,  Min_Slope_Angle (degrees), Max_Slope_Angle (degrees)",
    "soil": "cohesion,   phi,     uws,          diffus,   K-sat,    Theta-sat, Theta-res,Alpha",
    "cri": "cri(1), cri(2), ..., cri(nper)",
    "capt": "capt(1), capt(2), ..., capt(n), capt(n+1)",
    "slofil": "File name of slope angle grid (slofil)",
    "elevfil": "File name of digital elevation grid (elevfil)",
    "zonfil": "File name of property zone grid (zonfil)",
    "zfil": "File name of depth grid (zfil) ",
    "depfil": "File name of initial depth of water table grid   (depfil)",
    "rizerofil": "File name of initial infiltration rate grid   (rizerofil)",
    "rifil": "List of file name(s) of rainfall intensity for each period, (rifil())",
    "nxtfil": "File name of grid of D8 runoff receptor cell numbers (nxtfil)",
    "ndxfil": "File name of list of cells defining runoff computation order (ndxfil)",
    "dscfil": "File name of list of all runoff receptor cells  (dscfil)",
    "wffil": "File name of list of runoff weighting factors  (wffil)",
    "folder": "Folder where output grid files will be stored  (folder)",
    "suffix": "Identification code to be added to names of output files (suffix)",
    "rodoc": "Save grid files of runoff? Enter T (.true.) or F (.false.)",
    "outp2": "Save grid of minimum factor of safety? Enter T (.true.) or F (.false.)",
    "outp3": "Save grid of depth of minimum factor of safety? Enter T (.true.) or F (.false.)",
    "outp4": "Save grid of pressure head at depth of minimum factor of safety? Enter T (.true.) or F (.false.)",
    "outp1": "Save grid of computed water table depth or elevation? Enter T (.true.) or F (.false.) followed by 'depth,' or 'eleva'",
    "outp5": "Save grid files of actual infiltration rate? Enter T (.true.) or F (.false.)",
    "outp6": "Save grid files of unsaturated zone basal flux? Enter T (.true.) or F (.false.)",
    "flag": ("Save listing of pressure head and factor of safety (\"flag\")? "
             "(-9 sparse xmdv , -8 down-sampled xmdv, -7 full xmdv, -6 sparse ijz, "
             "-5 down-sampled ijz, -4 full ijz, -3 Z-P-Fs-saturation list "
             "-2 detailed Z-P-Fs, -1 Z-P-Fs list, 0 none). "
             "Enter flag value followed by down-sampling interval (integer)."),
    "nout": "Number of times to save output grids and (or) ijz/xmdv files",
    "tsav": "Times of output grids and (or) ijz / xmdv files",
    "lskip": "Skip other timesteps? Enter T (.true.) or F (.false.)",
    "lany": "Use analytic solution for fillable porosity?  Enter T (.true.) or F (.false.)",
    "llus": ("Estimate positive pressure head in rising water table zone "
             "(i.e. in lower part of unsat zone)?  Enter T (.true.) or F (.false.)"),
    "lps0": "Use psi0=-1/alpha? Enter T (.true.) or F (.false.) (False selects the default value, psi0=0)",
    "outp8": "Log mass balance results?   Enter T (.true.) or F (.false.)",
    "flowdir": "Flow direction (Enter \"gener\", \"slope\", or \"hydro\")",
    "bkgrof": ("Add steady background flux to transient infiltration rate to prevent drying "
               "beyond the initial conditions during periods of zero infiltration?"),
    "lasc": "Specify file extension for output grids. Enter T (.true.) for \".asc\" or F for \".txt\"",
    "lpge0": ("Ignore negative pressure head in computing factor of safety "
              "(saturated infiltration only)?   Enter T (.true.) or F (.false.)"),
    "igcapf": ("Ignore height of capillary fringe in computing pressure head "
               "for unsaturated infiltration option?   Enter T (.true.) or F (.false.)"),
    "deepz": ("Parameters for deep pressure-head estimate in SCOOPS ijz output: "
              "Depth below ground surface (positive, use negative value to cancel this option), "
              "pressure option (enter 'zero' , 'flow' , 'hydr' , or 'relh')"),
}

# soil 表格列 -> 语义名
SOIL_COLUMNS = ("cohesion", "phi", "uws", "diffus", "ksat", "theta_sat", "theta_res", "alpha")

#: 工程附加信息（图层绑定）的注释块标题。
#: 以 "#" 开头，官方程序会忽略；本模块读回时用它恢复图层选择。
ANNOTATION_HEADER = "# --- TRIGRS 工程附加信息（官方程序会忽略本段）---"
ANNOTATION_FOOTER = "# --- 附加信息结束 ---"


def parse_annotations(text: str) -> dict[str, str]:
    """
    读取输入文件末尾注释块里的 ``key = value`` 附加信息。

    TRIGRS 与 TopoIndex 的读取器都按行序读参数、且会忽略 ``#`` 之后的内容，
    因此把图层绑定写进注释块既不影响原版程序，也能被本模块读回。
    """
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


class TrigrsInputError(ValueError):
    """参数不完整或不合法时抛出，携带面向用户的中文说明。"""


@dataclass
class TrigrsInput:
    """界面上全部 TRIGRS 参数的结构化表示。"""

    title: str = "TRIGRS project"

    # 1. 程序控制参数
    tx: int = 1
    nmax: int = 30
    mmax: int = 100
    zones: int = 1

    # 2. 模拟控制参数
    nzs: int = 4
    zmin: float = 0.001
    uww: float = 9.8e3
    nper: int = 1
    t: float = 18000.0

    # 3. 初始条件参数
    zmax: float = -5.0
    depth: float = -2.4
    rizero: float = 1.0e-7
    slomin: float = 0.0
    slomax: float = 90.0

    # 4. 土壤分区参数：每行 8 个值，按 SOIL_COLUMNS 顺序
    soil: list[list[float]] = field(default_factory=list)

    # 5. 降雨参数
    cri: list[float] = field(default_factory=list)
    capt: list[float] = field(default_factory=list)
    rifil: list[str] = field(default_factory=list)

    # 6/7. 栅格与径流文件
    slofil: str = ""
    elevfil: str = ""
    zonfil: str = ""
    zfil: str = ""
    depfil: str = ""
    rizerofil: str = ""
    nxtfil: str = ""
    ndxfil: str = ""
    dscfil: str = ""
    wffil: str = ""

    # 8. 输出选项
    folder: str = ""
    suffix: str = ""
    rodoc: bool = False
    save_fs_min: bool = False
    save_zf_min: bool = False
    save_p_min: bool = False
    save_water_table: bool = False
    water_table_mode: str = "depth"
    save_infiltration: bool = False
    save_basal_flux: bool = False
    flag: int = 0
    spcg: int = 1
    nout: int = 1
    tsav: list[float] = field(default_factory=lambda: [0.0])
    lskip: bool = False
    lany: bool = True
    llus: bool = True
    lps0: bool = False
    log_mass_balance: bool = True
    flowdir: str = "gener"
    bkgrof: bool = True
    lasc: bool = True
    lpge0: bool = True
    igcapf: bool = True

    # 9. SCOOPS
    deepz: float = -50.0
    deepwat: str = "flow"


def _tf(value: bool) -> str:
    return "T" if value else "F"


def _num(value: float) -> str:
    """把浮点数写成 TRIGRS 能稳定解析的形式。"""
    if isinstance(value, bool):  # 防御：bool 是 int 的子类
        return _tf(value)
    if isinstance(value, int):
        return str(value)
    f = float(value)
    if not math.isfinite(f):
        raise TrigrsInputError(f"数值 {value!r} 不是有限数")
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return repr(f)


def _bool_from(value) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"t", "true", ".true.", "1", "yes", "y"}


def build_tr_in(data: TrigrsInput) -> str:
    """把 :class:`TrigrsInput` 渲染成 tr_in.txt 的完整文本。"""
    if data.zones < 1:
        raise TrigrsInputError("土壤分区数 zones 必须大于等于 1")
    if data.nper < 1:
        raise TrigrsInputError("降雨时段数 nper 必须大于等于 1")
    if data.nout < 1:
        raise TrigrsInputError("输出次数 nout 必须大于等于 1")
    if len(data.soil) != data.zones:
        raise TrigrsInputError(
            f"土壤参数表有 {len(data.soil)} 行，但 zones = {data.zones}，两者必须一致")
    for i, row in enumerate(data.soil, start=1):
        if len(row) != len(SOIL_COLUMNS):
            raise TrigrsInputError(
                f"第 {i} 个分区需要 {len(SOIL_COLUMNS)} 个参数，实际 {len(row)} 个")
    if len(data.cri) != data.nper:
        raise TrigrsInputError(
            f"cri 需要 {data.nper} 个值，实际 {len(data.cri)} 个")
    if len(data.capt) != data.nper + 1:
        raise TrigrsInputError(
            f"capt 需要 {data.nper + 1} 个值，实际 {len(data.capt)} 个")
    if len(data.rifil) != data.nper:
        raise TrigrsInputError(
            f"rifil 需要 {data.nper} 个文件，实际 {len(data.rifil)} 个")
    if len(data.tsav) != data.nout:
        raise TrigrsInputError(
            f"tsav 需要 {data.nout} 个值，实际 {len(data.tsav)} 个")
    if data.water_table_mode not in {"depth", "eleva"}:
        raise TrigrsInputError("水位输出形式只能是 depth 或 eleva")
    if data.flowdir not in {"gener", "slope", "hydro"}:
        raise TrigrsInputError("flowdir 只能是 gener / slope / hydro")
    if data.deepwat not in {"zero", "flow", "hydr", "relh"}:
        raise TrigrsInputError("deepwat 只能是 zero / flow / hydr / relh")

    out: list[str] = []

    out.append(H["title"])
    out.append(data.title.strip() or "TRIGRS project")

    out.append(H["control"])
    out.append(f"{int(data.tx)}, {int(data.nmax)}, {int(data.mmax)}, {int(data.zones)}")

    out.append(H["simulation"])
    out.append(
        f"{int(data.nzs)}, {_num(data.zmin)}, {_num(data.uww)}, "
        f"{int(data.nper)}, {_num(data.t)}"
    )

    out.append(H["condition"])
    # zmax / depth / rizero 在 TRIGRS 里是“标量或栅格”的开关，不是两者都要：
    # 见 TrigrsIO/ReadGrids.py::__read_soi_water_grids()——
    #   标量 <  0  -> 从对应的栅格文件读取
    #   标量 >= 0  -> 整幅图都用这个标量值（栅格文件被忽略）
    # 所以只要提供了栅格文件，就必须把标量写成负值，否则栅格会被静默忽略。
    zmax_val = -1 if str(data.zfil).strip() else data.zmax
    depth_val = -1 if str(data.depfil).strip() else data.depth
    rizero_val = -1 if str(data.rizerofil).strip() else data.rizero
    out.append(
        f"{_num(zmax_val)}, {_num(depth_val)}, {_num(rizero_val)}, "
        f"{_num(data.slomin)}, {_num(data.slomax)}"
    )

    for i, row in enumerate(data.soil, start=1):
        out.append(f"zone, {i}")
        out.append(H["soil"])
        out.append(", ".join(_num(v) for v in row))

    out.append(H["cri"])
    # cri(j) 同样是“标量或栅格”的开关，见 TrigrsSubroutine/Rnoff.py：
    #   cri(j) <  0 -> 从 rifil(j) 栅格读取该时段的降雨强度
    #   cri(j) >= 0 -> 该时段整幅图都用这个常数强度（栅格被忽略）
    # 因此某一时段只要指定了降雨栅格，就把该时段的 cri 写成 -1。
    cri_values = []
    for j in range(int(data.nper)):
        has_grid = j < len(data.rifil) and str(data.rifil[j]).strip()
        cri_values.append(-1 if has_grid else data.cri[j])
    out.append(", ".join(_num(v) for v in cri_values))

    out.append(H["capt"])
    out.append(", ".join(_num(v) for v in data.capt))

    out.append(H["slofil"])
    out.append(data.slofil)
    out.append(H["elevfil"])
    out.append(data.elevfil)
    out.append(H["zonfil"])
    out.append(data.zonfil)
    out.append(H["zfil"])
    out.append(data.zfil)
    out.append(H["depfil"])
    out.append(data.depfil)
    out.append(H["rizerofil"])
    out.append(data.rizerofil)

    out.append(H["rifil"])
    out.extend(data.rifil)

    out.append(H["nxtfil"])
    out.append(data.nxtfil)
    out.append(H["ndxfil"])
    out.append(data.ndxfil)
    out.append(H["dscfil"])
    out.append(data.dscfil)
    out.append(H["wffil"])
    out.append(data.wffil)

    out.append(H["folder"])
    out.append(data.folder)
    out.append(H["suffix"])
    out.append(data.suffix)

    out.append(H["rodoc"])
    out.append(_tf(data.rodoc))
    out.append(H["outp2"])
    out.append(_tf(data.save_fs_min))
    out.append(H["outp3"])
    out.append(_tf(data.save_zf_min))
    out.append(H["outp4"])
    out.append(_tf(data.save_p_min))
    out.append(H["outp1"])
    out.append(f"{_tf(data.save_water_table)}, {data.water_table_mode}")
    out.append(H["outp5"])
    out.append(_tf(data.save_infiltration))
    out.append(H["outp6"])
    out.append(_tf(data.save_basal_flux))

    out.append(H["flag"])
    out.append(f"{int(data.flag)},{int(data.spcg)}")

    out.append(H["nout"])
    out.append(str(int(data.nout)))
    out.append(H["tsav"])
    out.append(", ".join(_num(v) for v in data.tsav))

    out.append(H["lskip"])
    out.append(_tf(data.lskip))
    out.append(H["lany"])
    out.append(_tf(data.lany))
    out.append(H["llus"])
    out.append(_tf(data.llus))
    out.append(H["lps0"])
    out.append(_tf(data.lps0))

    out.append(H["outp8"])
    out.append(_tf(data.log_mass_balance))
    out.append(H["flowdir"])
    out.append(data.flowdir)
    out.append(H["bkgrof"])
    out.append(_tf(data.bkgrof))
    out.append(H["lasc"])
    out.append(_tf(data.lasc))
    out.append(H["lpge0"])
    out.append(_tf(data.lpge0))
    out.append(H["igcapf"])
    out.append(_tf(data.igcapf))
    out.append(H["deepz"])
    out.append(f"{_num(data.deepz)},{data.deepwat}")

    return "\n".join(out) + "\n"


def write_tr_in(data: TrigrsInput, path: str | os.PathLike) -> Path:
    """写出 tr_in.txt，返回实际写入的路径。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # TRIGRS 逐行读取，统一使用 LF 换行最稳妥
    target.write_text(build_tr_in(data), encoding="utf-8", newline="\n")
    return target


# --------------------------------------------------------------------------
# 读回（与官方 tr_in.txt 格式兼容，因此可以直接打开原版程序的文件）
# --------------------------------------------------------------------------
def _clean(line: str) -> str:
    """去掉行尾注释并去除首尾空白。"""
    return line.split("#", 1)[0].strip()


def _values(line: str, count: int) -> list[str]:
    """按逗号或空白切分一行，不足补空串。"""
    # 官方文件里逗号后面常常既有空格也有纯空白，统一替换成空格最省事
    text = _clean(line).replace(",", " ").replace(";", " ")
    parts = [p for p in text.split() if p]
    while len(parts) < count:
        parts.append("")
    return parts[:count]


def _to_bool(text: str) -> bool:
    return str(text).strip().lower() in {"t", "true", ".true."}


def looks_like_tr_in(path: str | os.PathLike) -> bool:
    """判断文件是否为 TRIGRS 输入文件（用首行说明行识别）。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    return stripped.lower().startswith("name of project")
    except OSError:
        return False
    return False


def parse_tr_in(path: str | os.PathLike) -> TrigrsInput:
    """
    解析官方 tr_in.txt，返回 :class:`TrigrsInput`。

    解析逻辑与 :func:`build_tr_in` 的写出顺序严格对应，因此可以读回原版
    TRIGRS 程序使用的输入文件。末尾的 ``#`` 注释块（本模块写入的图层绑定）
    会被自动忽略。
    """
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    # 注释行不参与参数解析（官方文件也可能带 # 注释）
    lines = [ln for ln in lines if not ln.strip().startswith("#")]
    if len(lines) < 10:
        raise TrigrsInputError("文件内容过少，不像是一个 tr_in.txt")

    # 文件是“说明行 + 值行”交替的固定行序，行数随 zones / nper 变化，
    # 因此按游标严格推进。注意有两处值行不止一行（soil 段的 zone 行、
    # rifil 段的每期一行），不能简单地一律“跳一行读一行”。
    cursor = 0
    total = len(lines)

    def skip_heading() -> None:
        """跳过一个“说明行”。"""
        nonlocal cursor
        if cursor < total:
            cursor += 1

    def next_value(label: str) -> str:
        """跳过一个“说明行”，返回并消费随后的值行。"""
        nonlocal cursor
        skip_heading()
        if cursor >= total:
            raise TrigrsInputError(f"文件在读取“{label}”时意外结束")
        value = _clean(lines[cursor])
        cursor += 1
        return value

    def read_value(label: str) -> str:
        """直接返回并消费下一行（用于说明行之后连续多行的情况）。"""
        nonlocal cursor
        if cursor >= total:
            raise TrigrsInputError(f"文件在读取“{label}”时意外结束")
        value = _clean(lines[cursor])
        cursor += 1
        return value

    title = next_value(H["title"])

    control = _values(next_value(H["control"]), 4)
    simulation = _values(next_value(H["simulation"]), 5)
    condition = _values(next_value(H["condition"]), 5)

    zones = int(float(control[3]))
    nper = int(float(simulation[3]))

    soil: list[list[float]] = []
    for i in range(zones):
        skip_heading()                                     # "zone, i"
        skip_heading()                                     # 参数名行
        soil.append([float(v) for v in _values(read_value(f"zone {i + 1}"), 8)])

    cri = [float(v) for v in _values(next_value(H["cri"]), nper)]
    capt = [float(v) for v in _values(next_value(H["capt"]), nper + 1)]

    slofil = next_value(H["slofil"])
    elevfil = next_value(H["elevfil"])
    zonfil = next_value(H["zonfil"])
    zfil = next_value(H["zfil"])
    depfil = next_value(H["depfil"])
    rizerofil = next_value(H["rizerofil"])

    # rifil 段是“说明行 + nper 行文件名”，不能按对读取
    skip_heading()
    rifil = [read_value(f"rifil({i + 1})") for i in range(nper)]

    nxtfil = next_value(H["nxtfil"])
    ndxfil = next_value(H["ndxfil"])
    dscfil = next_value(H["dscfil"])
    wffil = next_value(H["wffil"])
    folder = next_value(H["folder"])
    suffix = next_value(H["suffix"])

    rodoc = _to_bool(next_value(H["rodoc"]))
    save_fs_min = _to_bool(next_value(H["outp2"]))
    save_zf_min = _to_bool(next_value(H["outp3"]))
    save_p_min = _to_bool(next_value(H["outp4"]))

    water = _values(next_value(H["outp1"]), 2)
    save_water_table = _to_bool(water[0])
    water_table_mode = water[1] or "depth"

    save_infiltration = _to_bool(next_value(H["outp5"]))
    save_basal_flux = _to_bool(next_value(H["outp6"]))

    flag_spcg = _values(next_value(H["flag"]), 2)
    flag = int(float(flag_spcg[0]))
    spcg = int(float(flag_spcg[1])) if flag_spcg[1] else 1

    nout = max(1, int(float(next_value(H["nout"]))))
    tsav = [float(v) for v in _values(next_value(H["tsav"]), nout)]

    lskip = _to_bool(next_value(H["lskip"]))
    lany = _to_bool(next_value(H["lany"]))
    llus = _to_bool(next_value(H["llus"]))
    lps0 = _to_bool(next_value(H["lps0"]))
    log_mass_balance = _to_bool(next_value(H["outp8"]))

    flowdir = next_value(H["flowdir"]).strip() or "gener"
    bkgrof = _to_bool(next_value(H["bkgrof"]))
    lasc = _to_bool(next_value(H["lasc"]))
    lpge0 = _to_bool(next_value(H["lpge0"]))
    igcapf = _to_bool(next_value(H["igcapf"]))

    deep = _values(next_value(H["deepz"]), 2)
    deepz = float(deep[0]) if deep[0] else -50.0
    deepwat = deep[1] or "flow"

    def num(token: str, default: float = 0.0) -> float:
        return float(token) if token else default

    return TrigrsInput(
        title=title,
        tx=int(float(control[0] or 1)),
        nmax=int(float(control[1] or 30)),
        mmax=int(float(control[2] or 100)),
        zones=zones,
        nzs=int(float(simulation[0] or 4)),
        zmin=num(simulation[1]),
        uww=num(simulation[2], 9.8e3),
        nper=nper,
        t=num(simulation[4]),
        zmax=num(condition[0]),
        depth=num(condition[1]),
        rizero=num(condition[2]),
        slomin=num(condition[3]),
        slomax=num(condition[4], 90.0),
        soil=soil,
        cri=cri,
        capt=capt,
        rifil=rifil,
        slofil=slofil,
        elevfil=elevfil,
        zonfil=zonfil,
        zfil=zfil,
        depfil=depfil,
        rizerofil=rizerofil,
        nxtfil=nxtfil,
        ndxfil=ndxfil,
        dscfil=dscfil,
        wffil=wffil,
        folder=folder,
        suffix=suffix,
        rodoc=rodoc,
        save_fs_min=save_fs_min,
        save_zf_min=save_zf_min,
        save_p_min=save_p_min,
        save_water_table=save_water_table,
        water_table_mode=water_table_mode if water_table_mode in {"depth", "eleva"} else "depth",
        save_infiltration=save_infiltration,
        save_basal_flux=save_basal_flux,
        flag=flag,
        spcg=spcg,
        nout=nout,
        tsav=tsav,
        lskip=lskip,
        lany=lany,
        llus=llus,
        lps0=lps0,
        log_mass_balance=log_mass_balance,
        flowdir=flowdir if flowdir in {"gener", "slope", "hydro"} else "gener",
        bkgrof=bkgrof,
        lasc=lasc,
        lpge0=lpge0,
        igcapf=igcapf,
        deepz=deepz,
        deepwat=deepwat if deepwat in {"zero", "flow", "hydr", "relh"} else "flow",
    )


# --------------------------------------------------------------------------
# 校验
# --------------------------------------------------------------------------
def validate(data: TrigrsInput) -> tuple[list[str], list[str]]:
    """
    在不写文件的前提下检查参数。

    :return: ``(errors, warnings)``

    ``errors`` 是真正会阻止计算的问题；``warnings`` 只是提示，例如某个分区
    选择了饱和入渗模型。之所以分开，是因为 TRIGRS 本身允许很多“看起来异常”
    的取值（例如 ``alpha <= 0`` 表示改用饱和模型），把它们当成错误会让用户
    无法运行本来合法的配置。
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        build_tr_in(data)
    except TrigrsInputError as exc:
        return [str(exc)], warnings

    # 坡度、高程是必需栅格
    for label, value in (
        ("坡度栅格 slofil", data.slofil),
        ("高程栅格 elevfil", data.elevfil),
    ):
        if not str(value).strip():
            errors.append(f"未指定{label}")

    # zmax / depth / rizero 是“标量或栅格”二选一：
    # 给了栅格就用栅格；只给标量也可以，整幅图取该常数。
    # 只有两者都缺时才无法确定取值。
    scalar_grid_pairs = (
        ("最大深度", data.zmax, data.zfil, "zfil"),
        ("初始地下水位深度", data.depth, data.depfil, "depfil"),
        ("初始入渗率", data.rizero, data.rizerofil, "rizerofil"),
    )
    for label, scalar, grid, grid_name in scalar_grid_pairs:
        if not str(grid).strip() and scalar < 0:
            errors.append(
                f"{label}：未指定栅格 {grid_name}，且标量值为 {scalar}（负值表示" 
                f"“请从栅格读取”），两者都没有提供")

    # 属性分区：zones == 1 时 TRIGRS 不使用 zonfil
    if int(data.zones) > 1 and not str(data.zonfil).strip():
        errors.append("设置了多个土壤分区（zones > 1），但未指定属性分区栅格 zonfil")

    # cri(j) 与 rifil(j) 同样是二选一
    for j in range(int(data.nper)):
        path = str(data.rifil[j]).strip() if j < len(data.rifil) else ""
        cri = data.cri[j] if j < len(data.cri) else -1.0
        if not path and cri < 0:
            errors.append(
                f"第 {j + 1} 期降雨：未指定降雨栅格 rifil({j + 1})，"
                f"且 cri({j + 1}) = {cri}（负值表示“请从栅格读取”），两者都没有提供")

    runoff = [data.nxtfil, data.ndxfil, data.dscfil, data.wffil]
    filled = [bool(str(p).strip()) for p in runoff]
    if any(filled) and not all(filled):
        errors.append(
            "径流演算四个文件（nxtfil / ndxfil / dscfil / wffil）必须同时提供或全部留空")

    if not str(data.folder).strip():
        errors.append("未指定输出文件夹 folder")
    else:
        folder = Path(str(data.folder))
        if not folder.is_absolute():
            # 相对路径按输入文件所在目录解析，单独检查时无法确定，仅作提示
            warnings.append(f"输出文件夹是相对路径：{folder}（将以输入文件所在目录为基准）")
        elif not folder.is_dir():
            errors.append(f"输出文件夹不存在：{folder}")

    if data.slomin >= data.slomax:
        errors.append(f"最小坡度({data.slomin})必须小于最大坡度({data.slomax})")
    if data.slomax > 90.0 or data.slomax <= 0.0:
        errors.append("最大坡度应在 (0, 90] 度之间")
    if any(b <= a for a, b in zip(data.capt, data.capt[1:])):
        errors.append("capt 必须严格递增")
    if data.t < data.capt[0]:
        errors.append(f"模拟总时长 t({data.t}) 小于第一个降雨时段起点 capt(1)={data.capt[0]}")

    # 土壤参数：只有物理上不成立的才报错
    for i, row in enumerate(data.soil, start=1):
        values = dict(zip(SOIL_COLUMNS, row))
        # 粘聚力、重度、扩散系数、Ks 为负没有物理意义
        for name in ("cohesion", "uws", "diffus", "ksat"):
            if values[name] < 0:
                errors.append(f"第 {i} 个分区的 {name} 为负值")
        if not 0.0 <= values["phi"] <= 90.0:
            errors.append(f"第 {i} 个分区的内摩擦角 phi 应在 0~90 度之间，当前 {values['phi']}")
        for name in ("theta_sat", "theta_res"):
            if not 0.0 <= values[name] <= 1.0:
                errors.append(f"第 {i} 个分区的 {name} 应在 0~1 之间，当前 {values[name]}")
        if values["theta_sat"] < values["theta_res"]:
            errors.append(
                f"第 {i} 个分区的 Theta-sat({values['theta_sat']}) "
                f"小于 Theta-res({values['theta_res']})；"
                f"TRIGRS 会改用饱和入渗模型，建议修正")
        # alpha <= 0 是官方定义的做法，不是错误：表示该分区采用饱和入渗模型
        if values["alpha"] <= 0:
            warnings.append(
                f"第 {i} 个分区的 alpha = {values['alpha']} <= 0："
                f"按 TRIGRS 约定该分区采用饱和入渗模型（这是正常用法）")

    # 引用的栅格文件必须真实存在
    for label, value in (
        ("坡度栅格", data.slofil),
        ("高程栅格", data.elevfil),
        ("属性分区栅格", data.zonfil),
        ("最大深度栅格", data.zfil),
        ("初始地下水位深度栅格", data.depfil),
        ("初始入渗率栅格", data.rizerofil),
    ):
        if str(value).strip() and not Path(str(value)).exists():
            errors.append(f"{label}不存在：{value}")

    for i, path in enumerate(data.rifil, start=1):
        if str(path).strip() and not Path(str(path)).exists():
            errors.append(f"第 {i} 期降雨强度栅格不存在：{path}")

    for label, value in (
        ("nxtfil", data.nxtfil), ("ndxfil", data.ndxfil),
        ("dscfil", data.dscfil), ("wffil", data.wffil),
    ):
        if str(value).strip() and not Path(str(value)).exists():
            errors.append(f"径流演算文件 {label} 不存在：{value}")

    return errors, warnings
