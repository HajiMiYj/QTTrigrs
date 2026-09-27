"""
计算饱和和非饱和入渗的孔隙压力响应和安全系数的程序（对应 trigrs.f90）。

本版本把力学求解（steady / rnoff / savage / iverson / satinf / satfin /
unsinf / unsfin 及其辅助过程）全部交给 Fortran(f2py) 内核
:mod:`.trigrs_fortran`，Python 侧负责：
  1. IO：读输入文件、读栅格、写结果栅格；
  2. 列表输出（flag<0 时的 ijz / Z-P-Fs 详细列表）。
"""
import sys

import numpy as np

from run_control import StopRequested, yield_

from .TrigrsIO.CheckLogFilePath import __check_log_file_path
from .TrigrsIO.PrintTrigrsTitle import __print_trigrs_title
from .TrigrsIO.ReadGrids import __read_grid_size, __read_soi_water_grids, __read_slo
from .TrigrsModule.Grids import grids
from .TrigrsModule.InputFileDefs import input_file_defs
from .TrigrsModule.InputVars import input_vars
from .TrigrsModule.ModelVars import model_vars
from .TrigrsSubroutine.Prpijz import prpijz
from .TrigrsSubroutine.Ssvgrd import ssvgrd
from .TrigrsSubroutine.Svijz import svijz
from .TrigrsSubroutine.Svlist import svlist
from .TrigrsSubroutine.Srdgrd import srdgrd
from .TrigrsSubroutine.TriNi import trini
from .TrigrsUtils.InitTrigrsVars import __init_trigrs_vars
from .TrigrsUtils.MessageRequest import VerboseMessage
from .TrigrsUtils.OptimizeGroundwater import optimize_groundwater
from .trigrs_fortran import run_fortran_mechanics, write_runoff_grids


def trigrs(tr_in_file: str = "tr_in.txt", log_file_path: str = "TrigrsLog.txt",
           stop_event=None):
    """
    主程序，对应于 trigrs.f90

    :param tr_in_file: 初始化文件(tr_in.txt)的路径。
    :param log_file_path: 运行日志文件路径，默认当前目录 TrigrsLog.txt。
    :param stop_event: 可选 threading.Event，置位后中断输出阶段。
    """
    # ========== 初始化变量 ==================
    fminfil, zfminfil, pminfil, profil, date, time, pid, vrsn, bldate, wtabfil = __init_trigrs_vars()
    __print_trigrs_title(vrsn, bldate)

    # ========== 读输入文件 ==================
    log_file = __check_log_file_path(log_file_path, vrsn, bldate, date, time)
    verbose_message = VerboseMessage(log_file)
    trini(verbose_message, tr_in_file, model_vars.dg2rad)

    # 读取栅格尺寸
    grd, imx1 = __read_grid_size(pid, verbose_message)

    # ========== 读栅格 ==================
    sctr, ncol, nrow, header = __read_slo(verbose_message, grd)

    sctr, ncol, nrow, header = __read_soi_water_grids(sctr, ncol, nrow, header, grd, "读取渗入率栅格",
                                                      verbose_message, grids.rizero,
                                                      input_vars.crizero, input_file_defs.rizerofil)
    sctr, ncol, nrow, header = __read_soi_water_grids(sctr, ncol, nrow, header, grd, "读取地下水位深度栅格",
                                                      verbose_message, grids.depth,
                                                      input_vars.dep, input_file_defs.depfil)
    _, _, _, _ = __read_soi_water_grids(sctr, ncol, nrow, header, grd, "读取最大深度栅格",
                                        verbose_message, grids.zmax, input_vars.czmax, input_file_defs.zfil)

    optimize_groundwater()

    info_message = "读取高程栅格"
    print(info_message)
    sctr, ncol, nrow, _grids_param, header, _ = srdgrd(grd, grids.elev, input_file_defs.elevfil, log_file)
    log_file.write(f"{info_message}\n{input_file_defs.elevfil}\t{sctr}栅格单元\n")
    if sctr != input_vars.imax or ncol != input_vars.col or nrow != input_vars.row:
        log_file.write(f"TRIGRS主程序中的栅格不匹配：{input_file_defs.elevfil}\n")
        log_file.close()
    log_file.write("---------------******---------------\n")

    # ========== 力学求解（Fortran 内核）==========
    ncc, nccs = run_fortran_mechanics(grd, imx1, ncol, nrow, log_file)
    yield_(stop_event)
    write_runoff_grids(imx1, ncol, nrow, log_file, stop_event)

    # ========== 列表输出准备（flag<0）==========
    ijz_files = None
    if input_vars.flag < 0:
        model_vars.zmn = np.array([float(np.min(grids.elev))])
        model_vars.zmx = np.array([float(np.max(grids.elev))])
        ijz_files = prpijz(verbose_message, profil, input_vars.col, input_vars.row, header, vrsn)

    # ========== 写出结果栅格与列表 ==========
    model_vars.ti = np.finfo(type(model_vars.param[0])).tiny
    verbose_message.message_request(info_message="保存结果")

    folder = input_file_defs.folder
    suffix = input_file_defs.suffix
    grxt = grids.grxt
    nout = input_vars.nout
    imax = input_vars.imax
    nzs = input_vars.nzs
    row = input_vars.row
    col = input_vars.col

    for j in range(nout):
        stp = str(j + 1)
        yield_(stop_event)
        if input_vars.outp[2]:
            ssvgrd(grids.fsmin[j * imax:(j + 1) * imax], grids.pf1, row, col,
                   model_vars.test1, model_vars.param, log_file,
                   f"{folder}{fminfil}{suffix}_{stp}{grxt}")
        yield_(stop_event)
        if input_vars.outp[3]:
            ssvgrd(grids.zfmin[j * imax:(j + 1) * imax], grids.pf1, row, col,
                   model_vars.test1, model_vars.param, log_file,
                   f"{folder}{zfminfil}{suffix}_{stp}{grxt}")
        yield_(stop_event)
        if input_vars.outp[4]:
            ssvgrd(grids.pmin[j * imax:(j + 1) * imax], grids.pf1, row, col,
                   model_vars.test1, model_vars.param, log_file,
                   f"{folder}{pminfil}{suffix}_{stp}{grxt}")

        # 水位面（outp(1)）与 ijz 列表（flag -4..-6）：逐单元标量由胶水层算好
        if input_vars.flag <= -4 or input_vars.outp[0]:
            if input_vars.flag >= -6:
                for i in range(imax):
                    if i % 10000 == 0:
                        yield_(stop_event)
                    newdep = model_vars.newdep3d[i + j * imax]
                    dh = model_vars.dh3d[i + j * imax]
                    model_vars.p[:] = model_vars.p3d[i + j * imax, :]
                    model_vars.thz[:] = model_vars.th3d[i + j * imax, :]
                    svijz(i, j, dh, newdep, verbose_message, ijz_files,
                          model_vars.dcf_cell[i], model_vars.beta_cell[i], model_vars.p0zmx_cell[i])

        yield_(stop_event)
        if input_vars.outp[0]:
            ssvgrd(grids.wtab[j * imax:(j + 1) * imax], grids.pf1, row, col,
                   model_vars.test1, model_vars.param, log_file,
                   f"{folder}{wtabfil}{input_vars.el_or_dep}_{suffix}_{stp}{grxt}")

        if -3 <= input_vars.flag <= -1:
            svlist(ijz_files[0], stop_event)

    # 关闭未关闭的列表文件（svlist 已自行关闭 ijz_files[0]）
    if ijz_files:
        for _f in ijz_files:
            if _f is not None and not _f.closed:
                _f.close()

    log_file.write("TRIGRS 计算结束\n")
    log_file.flush()


if __name__ == '__main__':
    try:
        _argv = sys.argv[1:]
        trigrs(*_argv)
    except Exception as e:
        print(f'程序执行出现错误: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)
