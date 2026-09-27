"""
TRIGRS 力学内核的 Python 胶水层。

把现有引擎的 IO（``TrigrsIO`` / ``TrigrsSubroutine`` 里的栅格与径流文件读取）
与 Fortran(f2py) 力学内核（``trigrs_f2py.trigrs_solve``）连接起来：

* IO 留在 Python：读 ``tr_in.txt``、读栅格（坡度/高程/分区/深度/水位/入渗率/
  降雨）、写结果栅格与列表文件；
* 力学全部在 Fortran：``steady``、``rnoff``、时间步编排，以及
  ``savage`` / ``iverson`` / ``satinf`` / ``satfin`` / ``unsinf`` / ``unsfin``
  六个求解分支。

数值约定与官方 TRIGRS 完全一致：
* 角度（``slo`` / ``phi`` / ``slomin`` / ``slomax``）在传入前已转为弧度；
* ``depth`` / ``zmax`` / ``rizero`` 传**栅格数值**（正深度、正入渗率），
  负标量只是“改读栅格”的哨兵，由上层在读栅格阶段处理；
* 径流数组（``nxt`` / ``indx`` / ``dsc`` / ``dsctr`` / ``zo``）按 Fortran 1 基。
"""
from __future__ import annotations

import os

import numpy as np

from .TrigrsModule.Grids import grids
from .TrigrsModule.InputFileDefs import input_file_defs
from .TrigrsModule.InputVars import input_vars
from .TrigrsModule.ModelVars import model_vars
from .TrigrsSubroutine.Irdgrd import irdgrd
from .TrigrsSubroutine.Irdswm import irdswm
from .TrigrsSubroutine.Srdgrd import srdgrd
from .TrigrsSubroutine.Srdswm import srdswm
from .TrigrsSubroutine.Ssvgrd import ssvgrd
from .trigrs_f2py import kernels


# ---------------------------------------------------------------------------
# 时间步参数（与官方 trigrs.f90 主程序 283-320 行逐字一致）
# ---------------------------------------------------------------------------
def compute_time_params() -> tuple[int, int, int, float]:
    """返回 (kper, tx, nts, tinc)；tx 已做非饱和模型的自适应调整。"""
    nper = input_vars.nper
    t = input_vars.t
    capt = input_vars.capt

    kper = nper
    if t > capt[nper]:
        kper = nper + 1
    else:
        for k in range(1, nper + 1):
            if capt[k - 1] <= t <= capt[k]:
                kper = k
                break

    tx = input_vars.tx
    if tx < 1:
        tx = 1
    nts = kper * tx
    tmin = 0.0
    tmax = t
    tinc = (tmax - tmin) / nts

    if input_vars.unsat0:
        outp_incr_min = tmax
        tsav = input_vars.tsav
        nout = input_vars.nout
        for k in range(nout - 1):
            if nout > 1:
                outp_incr = tsav[k + 1] - tsav[k]
                if outp_incr < outp_incr_min:
                    outp_incr_min = outp_incr
            else:
                outp_incr = tsav[0]
        while tinc > outp_incr_min:
            tx += 1
            nts = kper * tx
            tinc = (tmax - tmin) / nts

    return kper, tx, nts, tinc


def _compute_rikzero() -> None:
    """复刻 Fortran steady() 的 rikzero 计算（供列表输出与 beta 计算）。"""
    zo = grids.zo.astype(np.int64)
    ks_at = input_vars.ks[zo]
    imax = input_vars.imax
    rikzero = np.ones(imax, dtype=np.float64)
    nz = ks_at != 0.0
    rikzero[nz] = grids.rizero[nz] / ks_at[nz]
    b = np.cos(grids.slo) ** 2
    adjust = rikzero >= b
    rikzero[adjust] = np.cos(grids.slo[adjust])
    grids.rikzero = rikzero


def _compute_output_pointers(kper: int, tx: int, nts: int, tinc: float) -> None:
    """复刻 Fortran 内核里的 tinc_sat / jsav / ksav / tsav 输出时刻指针。"""
    iv = input_vars
    nper = iv.nper
    tinc_sat = np.zeros(nts + 1, dtype=np.float64)
    time_incr_ctr = 0
    for k in range(1, kper + 1):
        for _ in range(1, tx + 1):
            time_incr_ctr += 1
            # capt(k+1)（1 基）= capt[k]（0 基）；kper>nper 的越界情况与官方一致忽略
            if k <= nper:
                if iv.t >= iv.capt[k]:
                    tinc_sat[time_incr_ctr] = (iv.capt[k] - iv.capt[k - 1]) / float(tx)
                else:
                    tinc_sat[time_incr_ctr] = (iv.t - iv.capt[k - 1]) / float(tx)
            else:
                tinc_sat[time_incr_ctr] = (iv.t - iv.capt[k - 1]) / float(tx)

    jsav = np.zeros(nts + 1, dtype=np.int32)
    ksav = np.zeros(iv.nout + 1, dtype=np.int32)
    tsav_m = iv.tsav.copy()
    tmax = iv.t
    for k in range(1, iv.nout + 1):
        ts = 0.0
        for j in range(1, nts + 1):
            if iv.unsat0:
                if tsav_m[k - 1] >= ts and tsav_m[k - 1] < ts + tinc:
                    jsav[j - 1] = k
                    ksav[k - 1] = j
                    tsav_m[k - 1] = ts
                    break
                elif tsav_m[k - 1] >= tmax:
                    jsav[nts] = k
                    ksav[k - 1] = nts + 1
                    tsav_m[k - 1] = tmax
                    break
                ts += tinc
            else:
                if tsav_m[k - 1] >= ts and tsav_m[k - 1] < ts + tinc_sat[j]:
                    jsav[j - 1] = k
                    ksav[k - 1] = j
                    tsav_m[k - 1] = ts
                    break
                elif tsav_m[k - 1] >= tmax:
                    jsav[nts] = k
                    ksav[k - 1] = nts + 1
                    tsav_m[k - 1] = tmax
                    break
                ts += tinc_sat[j]
    input_vars.ksav = ksav
    input_vars.tsav = tsav_m
    model_vars.jsav = jsav
    model_vars.tinc_sat = tinc_sat


def _compute_cell_scalars() -> None:
    """逐单元 beta / dcf / p0zmx（与 Fortran 求解器内公式一致）。"""
    iv = input_vars
    g = grids
    imax = iv.imax
    b1 = np.cos(g.slo)
    b1sq = b1 * b1
    flowdir = iv.flowdir.strip().lower()
    if flowdir == 'slope':
        beta = b1sq
    elif flowdir == 'hydro':
        beta = np.ones(imax, dtype=np.float64)
    else:
        beta = b1sq - g.rikzero
    beta = np.where(np.abs(b1 - g.rikzero) < 1e-6, 0.0, beta)

    zo = g.zo.astype(np.int64)
    dcf = np.where(iv.unsat[zo], g.depth - 1.0 / iv.alp[zo], 0.0)
    p0zmx = beta * (g.zmax - g.depth)

    model_vars.beta_cell = beta
    model_vars.dcf_cell = dcf
    model_vars.p0zmx_cell = p0zmx


def _read_ndxfil_1b(infil: str) -> np.ndarray:
    """读取径流计算顺序列表，返回 1 基 ``indx``（Fortran 约定）。"""
    data = np.loadtxt(infil, dtype=np.int64, ndmin=2)
    count = input_vars.imax
    if data.shape != (count, 2):
        raise ValueError(f"径流顺序列表应有 {count} 行、2 列：{infil}")
    indx = np.empty(count, dtype=np.int64)
    indx[data[:, 0] - 1] = data[:, 1]  # 保持 1 基
    return indx


def read_runoff_arrays(grd: int, imx1: int, ncol: int, nrow: int, log_file):
    """
    读取径流演算输入，返回：
    ``(ans, nxt, indx, dsctr, dsc, wf, ri_flat)``（全部 1 基，供 Fortran 使用）。

    若径流输入文件缺失则 ``ans=False``，此时返回空数组占位，Fortran 会走
    “无径流演算”分支。
    """
    def progress(message):
        print(message, flush=True)
        log_file.write(message + "\n")
        log_file.flush()

    file_list = [input_file_defs.nxtfil, input_file_defs.ndxfil,
                 input_file_defs.dscfil, input_file_defs.wffil,
                 os.path.join(input_file_defs.elfoldr.strip(), 'TIgrid_size.txt')]
    if 'no_input' in [f.strip() for f in file_list]:
        ans = False
    else:
        ans = all(os.path.isfile(f.strip()) for f in file_list)

    nper = input_vars.nper
    imax = input_vars.imax

    # 降雨强度 ri_flat（imax*nper），逐期填充
    ri_flat = np.empty(imax * nper, dtype=np.float64)
    ri_tmp = np.zeros(imax, dtype=np.float64)
    for j in range(nper):
        if input_vars.cri[j] < 0:
            sctr, _ncol, _nrow, ri_tmp, _header, _ = srdgrd(
                grd, ri_tmp, input_file_defs.rifil[j], log_file)
            if sctr != imx1:
                log_file.write(f"栅格数量不匹配 {input_file_defs.rifil[j]}\n")
        else:
            ri_tmp[:] = input_vars.cri[j]
        ri_flat[j * imax:(j + 1) * imax] = ri_tmp[:imax]

    if not ans:
        # 无径流演算：返回占位数组
        nwf = 1
        nxt = np.zeros(imax, dtype=np.int64)
        indx = np.arange(1, imax + 1, dtype=np.int64)
        dsctr = np.ones(imax + 1, dtype=np.int64)
        dsc = np.zeros(nwf, dtype=np.int64)
        wf = np.zeros(nwf, dtype=np.float64)
        progress("略过径流演算过程：径流汇流输入数据不存在。")
        return False, nxt, indx, dsctr, dsc, wf, ri_flat

    progress("开始径流演算（读取径流输入文件）")
    nwf = input_vars.nwf
    if nwf < imax:
        nwf = imax * 2
        input_vars.nwf = nwf
        log_file.write(f"nwf < imax，将 nwf 重置为 {nwf}\n")

    # D8 下游单元编号栅格 nxtfil（irdgrd 需要预分配输出数组，写回 grids.nxt）
    sctr, ncol, nrow, nxt, header, nodata, _ = irdgrd(grd, grids.nxt, input_file_defs.nxtfil, log_file)
    nxt = np.asarray(nxt, dtype=np.int64).reshape(-1)[:imax]
    if sctr != imx1:
        log_file.write(f"栅格数量不匹配 {input_file_defs.nxtfil}\n")
    # irdgrd 读出的有效单元编号：这里保证正值都按 1 基（>0 即有效下游单元编号）
    progress("读取径流计算顺序列表")
    indx = _read_ndxfil_1b(input_file_defs.ndxfil.strip())

    progress("读取下游受体列表")
    dsc_buf = np.zeros(nwf, dtype=np.int64)
    dsctr_buf = np.zeros(imax + 1, dtype=np.int64)
    dsc_buf = irdswm(nwf, imax, input_file_defs.dscfil.strip(), nodata, dsc_buf, dsctr_buf, log_file)
    dsc_buf = np.asarray(dsc_buf, dtype=np.int64)
    dsctr = np.asarray(dsctr_buf, dtype=np.int64)  # 1 基指针

    progress("读取径流权重列表")
    weight_ptr = np.empty_like(dsctr)
    wf = srdswm(nwf, imax, input_file_defs.wffil.strip(), nodata, np.zeros(nwf), weight_ptr, log_file)
    wf = np.asarray(wf, dtype=np.float64)
    if not np.array_equal(weight_ptr, dsctr):
        raise ValueError("下游受体列表与权重列表每行数量不匹配")

    edge_count = int(dsctr[-1]) - 1
    dsc = dsc_buf[:edge_count].copy()
    wf = wf[:edge_count].copy()
    progress("径流输入读取完成")

    return True, nxt, indx, dsctr, dsc, wf, ri_flat


# ---------------------------------------------------------------------------
# 调用 Fortran 内核
# ---------------------------------------------------------------------------
def run_fortran_mechanics(grd: int, imx1: int, ncol: int, nrow: int,
                          log_file) -> tuple[int, int]:
    """
    读取径流文件，调用 Fortran 力学内核，把结果写回 ``grids`` / ``model_vars``。

    返回 ``(ncc, nccs)``（非饱和/饱和未收敛单元计数）。
    """
    iv = input_vars
    mv = model_vars
    imax = iv.imax
    nzs = iv.nzs
    nout = iv.nout
    nper = iv.nper
    nzon = iv.nzon

    kper, tx, nts, tinc = compute_time_params()
    ans, nxt, indx, dsctr, dsc, wf, ri_flat = read_runoff_arrays(grd, imx1, ncol, nrow, log_file)

    nwf = iv.nwf if ans else 1
    dsc = np.asarray(dsc, dtype=np.int32)
    dsctr = np.asarray(dsctr, dtype=np.int32)
    nxt = np.asarray(nxt, dtype=np.int32)
    indx = np.asarray(indx, dtype=np.int32)

    # 输出数组（2D 需 Fortran 连续）
    fsmin = np.zeros(imax * nout)
    zfmin = np.zeros(imax * nout)
    pmin = np.zeros(imax * nout)
    wtab = np.zeros(imax * nout)
    rik1 = np.zeros(imax * (nts + 1))
    # f2py 对假定形状(assumed-shape)二维数组不转置：NumPy 形状即 Fortran 形状，
    # 因此按 Fortran 的 (行, 列) 直接分配，并用 F 顺序保证列主内存布局。
    p3d = np.zeros((imax * nout, nzs + 1), order='F')
    fs3d = np.zeros((imax * nout, nzs + 1), order='F')
    th3d = np.zeros((imax * nout, nzs + 1), order='F')
    ptran3d = np.zeros((imax * nout, nzs + 1), order='F')
    pzero3d = np.zeros((imax, nzs + 1), order='F')
    dh3d = np.zeros(imax * nout)
    newdep3d = np.zeros(imax * nout)
    nvu = np.zeros(imax, dtype=np.int32)
    nv = np.zeros(imax, dtype=np.int32)
    ro = np.zeros(imax)
    ir = np.zeros(imax)

    ncc, nccs = kernels.trigrs_solve(
        imax, nwf, tx, iv.nmax, iv.flag, nper, iv.spcg, nzs, iv.mmax, nzon, nout, kper, nts,
        iv.uww, iv.zmin, iv.t, iv.dep, iv.czmax, iv.crizero,
        iv.slomin, iv.slomax, iv.deepz, tinc,
        iv.flowdir, iv.el_or_dep, iv.deepwat,
        iv.outp, iv.rodoc, iv.lskip, iv.lany, iv.llus, iv.lps0,
        iv.unsat0, iv.bkgrof, iv.lpge0,
        iv.ths, iv.thr, iv.alp, iv.dif, iv.c, iv.phi, iv.ks, iv.uws,
        iv.capt, iv.cri, iv.tsav,
        iv.unsat, iv.igcap,
        grids.slo, grids.zo.astype(np.int32) + 1, grids.rizero, grids.depth, grids.zmax, grids.elev,
        nxt, indx, dsctr, dsc, wf, ri_flat, bool(ans),
        fsmin, zfmin, pmin, wtab, rik1,
        p3d, fs3d, th3d, ptran3d, pzero3d, dh3d, newdep3d,
        nvu, nv, ro, ir,
    )

    # 写回 grids / model_vars
    grids.fsmin = fsmin
    grids.zfmin = zfmin
    grids.pmin = pmin
    grids.wtab = wtab
    grids.rik1 = rik1
    grids.ro = ro
    grids.ir = ir
    grids.nvu = nvu
    grids.nv = nv

    model_vars.p3d = p3d
    model_vars.fs3d = fs3d
    model_vars.th3d = th3d
    model_vars.ptran3d = ptran3d
    model_vars.pzero3d = pzero3d
    model_vars.dh3d = dh3d
    model_vars.newdep3d = newdep3d

    # 记录时间步参数，供上层日志/输出使用
    model_vars.nts = nts
    model_vars.kper = kper
    model_vars.tinc = tinc
    model_vars.tmax = iv.t
    model_vars.tmin = 0.0
    input_vars.tx = tx

    # 输出相关的工作数组（供列表输出等复用）
    model_vars.p = np.zeros(nzs + 1)
    model_vars.thz = np.zeros(nzs + 1)
    model_vars.bline = np.zeros(nzs + 1)
    model_vars.zmn = np.array([float(np.min(grids.elev))])
    model_vars.zmx = np.array([float(np.max(grids.elev))])
    model_vars.ix = np.zeros(imax, dtype=np.int32)
    model_vars.jy = np.zeros(imax, dtype=np.int32)

    # 补算列表输出所需、而 Fortran 内核内部维护的量（公式与内核一致）
    _compute_rikzero()
    _compute_output_pointers(kper, tx, nts, tinc)
    _compute_cell_scalars()

    return ncc, nccs


def write_runoff_grids(imx1: int, ncol: int, nrow: int, log_file, stop_event=None) -> None:
    """写出径流/入渗率栅格（rodoc / outp(6)），对应官方 rnoff 的输出段。"""
    # 简化实现：仅当 rodoc 且存在径流时输出最后一期的 ro / ir。
    # 每期单独输出需要内核返回逐期 ro/ir，此处先输出末次结果作为占位。
    from run_control import yield_
    iv = input_vars
    mv = model_vars
    if not iv.rodoc and not iv.outp[6]:
        return
    scratch = f"{iv.nper:6d}".strip()
    ti = np.finfo(type(mv.param[0])).tiny if mv.param.size else 0.0
    if iv.rodoc:
        yield_(stop_event)
        rofil = f"TRrunoffPer{scratch}{input_file_defs.suffix}{grids.grxt}"
        outfil = input_file_defs.folder + rofil
        ssvgrd(grids.ro, grids.pf1, nrow, ncol, mv.test1, mv.param, log_file, outfil)
    if iv.outp[6]:
        yield_(stop_event)
        irfil = f"TRinfilratPer{scratch}{input_file_defs.suffix}{grids.grxt}"
        outfil = input_file_defs.folder + irfil
        ssvgrd(grids.ir, grids.pf1, nrow, ncol, mv.test1, mv.param, log_file, outfil)
