import os

import numpy as np

from ..TrigrsModule.Grids import grids
from ..TrigrsModule.InputFileDefs import input_file_defs
from ..TrigrsModule.InputVars import input_vars
from ..TrigrsModule.ModelVars import model_vars
from ..TrigrsSubroutine.Irdgrd import irdgrd
from ..TrigrsSubroutine.Srdgrd import srdgrd
from ..TrigrsSubroutine.Ssizgrd import ssizgrd
from ..TrigrsSubroutine.TriNi import __read_value_from_lines
from ..TrigrsUtils.MessageRequest import VerboseMessage


def __read_grid_size(pid: list, verbose_message: VerboseMessage):
    """
    读取栅格尺寸，先从elfoldr里读，读不了就调用ssizgrd来读
    grd是栅格总数，imx1是有效像元个数
    :param pid:pid = ['Ti', 'GM', 'TR']
    :param verbose_message:消息处理实例
    """
    infil = ""
    input_file_defs.elfoldr = os.path.dirname(input_file_defs.elevfil) + os.sep
    input_vars.ans = False
    for i in range(3):
        infil = os.path.join(input_file_defs.elfoldr, pid[i] + "grid_size.txt")
        input_vars.ans = os.path.exists(infil)
        if input_vars.ans:
            break
    # 如果能找到grid_size.txt，就读它
    if input_vars.ans:
        grid_size_file = open(infil, "r")
        input_file_defs.heading = grid_size_file.readline().strip()
        line = grid_size_file.readline().strip()
        imax, row, col, nwf = __read_value_from_lines(line, 4)
        input_vars.imax = int(imax)
        input_vars.row = int(row)
        input_vars.col = int(col)
        input_vars.nwf = int(nwf)
        grid_size_file.close()
    # 如果找不到，就读栅格
    else:
        """
        行数、列数、像元大小、空值字段、有效像元个数
        row, col, celsiz, nodat, ctr, header"""
        infil = input_file_defs.elevfil
        input_vars.row, input_vars.col, model_vars.celsiz, model_vars.nodat, input_vars.imax = ssizgrd(infil,
                                                                                                       verbose_message)
        outfil = os.path.join(input_file_defs.elfoldr, f"{pid[2]}grid_size.txt")
        # u(22)对应于grid_size_file
        grid_size_file = open(outfil, "w")
        grid_size_file.write('imax      row      col      nwf\n')
        # dsctr 由 TopoIndex 计算得出；dsctr = 1 是默认值，表示不进行径流汇流计算。
        input_vars.nwf = 1
        grid_size_file.write(f"{input_vars.imax}      {input_vars.row}      {input_vars.col}      {input_vars.nwf}\n")
    input_vars.ans = False
    # u(19)对应于log_file
    info_message = (f"栅格尺寸参数来自{infil}\n"
                    f"{input_file_defs.heading}\n"
                    f"{input_vars.imax}      {input_vars.row}      {input_vars.col}      {input_vars.nwf}\n")
    verbose_message.message_request(info_message=info_message)
    grd = input_vars.row * input_vars.col
    imx1 = input_vars.imax

    grids.pf2 = np.zeros(grd, dtype=int)  # pf2(grd)
    grids.indx = np.zeros(input_vars.imax, dtype=int)  # indx(imax)
    grids.nxt = np.zeros(input_vars.imax, dtype=int)  # nxt(imax)

    grids.dsctr = np.zeros(input_vars.imax + 1, dtype=int)  # dsctr(imax+1)
    grids.slo = np.zeros(input_vars.imax)  # slo(imax)

    grids.pf1 = np.zeros(grd)  # pf1(grd)
    grids.rizero = np.zeros(input_vars.imax)  # rizero(imax)

    grids.ri = np.zeros(input_vars.imax)  # ri(imax)
    grids.rik = np.zeros(input_vars.imax * input_vars.nper)  # rik(imax*nper)
    grids.ro = np.zeros(input_vars.imax)  # ro(imax)

    grids.rikzero = np.zeros(input_vars.imax)  # rikzero(imax)
    grids.temp = np.zeros(input_vars.col)  # temp(col)
    grids.itemp = np.zeros(input_vars.col, dtype=int)  # itemp(col)

    grids.depth = np.zeros(input_vars.imax)  # depth(imax)
    grids.zmax = np.zeros(input_vars.imax)  # zmax(imax)

    grids.zo = np.ones(input_vars.imax, dtype=int)  # zo(imax)，如需全1初始化
    grids.ir = np.zeros(input_vars.imax)  # ir(imax)
    grids.tfg = np.zeros(input_vars.imax)  # tfg(imax)

    grids.elev = np.zeros(input_vars.imax)  # elev(imax)
    return grd, imx1


def __read_soi_water_grids(sctr, ncol, nrow, header, grd, info_message, verbose_message,
                           grids_param, input_vars_param, input_file_defs_params):
    if input_vars_param < 0:
        sctr, ncol, nrow, grids_param, header, _ = srdgrd(grd, grids_param, input_file_defs_params, verbose_message)
        info_message = (f"{info_message}\n"
                        f"{input_file_defs_params}\t{sctr}栅格单元\n")
        verbose_message.message_request(info_message=info_message)
        if sctr != input_vars.imax or ncol != input_vars.col or nrow != input_vars.row:
            info_message = f"TRIGRS主程序中的栅格不匹配：{input_file_defs_params}\n"
            verbose_message.message_request(info_message=info_message)
    else:
        grids_param[:] = input_vars_param
    return sctr, ncol, nrow, header


def __read_slo(verbose_message, grd):
    """
    读取坡度栅格文件（slofil），并将其值转换为弧度（乘以dg2rad）。
    检查坡度栅格的行列数和单元数是否与高程网格一致，若不一致则发出警告。
    如果只有一个区域（nzon == 1），则将区域数组全部赋值为1，无需进一步划分。
    如果有多个区域，则读取区域划分栅格（zonfil），并将其索引从1基准转为0基准，同时检查其尺寸是否与高程网格一致，不一致则抛出异常。
    :param verbose_message: 消息处理实例
    :param grd: 栅格总数
    :return: sctr, ncol, nrow, header
    其中，sctr是有效栅格单元数，ncol是列数，nrow是行数，header是栅格文件头信息
    """
    info_message = "读取输入栅格"
    verbose_message.message_request(info_message=info_message)

    sctr, ncol, nrow, grids.slo, header, _ = srdgrd(grd, grids.slo, input_file_defs.slofil, verbose_message)
    info_message = (f"读取坡度\n"
                    f"{input_file_defs.slofil}\t\t\t{sctr}栅格单元\n")
    verbose_message.message_request(info_message=info_message)
    if sctr != input_vars.imax or ncol != input_vars.col or nrow != input_vars.row:
        warn_message = (f"栅格数量不匹配{input_file_defs.slofil}\n"
                        f"检查坡度栅格与高程网格是否一致。\n")
        verbose_message.message_request(warn_message=warn_message)
        pass
    grids.slo = grids.slo * model_vars.dg2rad

    if input_vars.nzon == 1:
        grids.zo = np.zeros(input_vars.imax, dtype=int)
        info_message = f"仅有一个区域，无需划分栅格"
        verbose_message.message_request(info_message=info_message)
        model_vars.parami = model_vars.param
    else:
        sctr, ncol, nrow, grids.zo, header, nodata, _ = irdgrd(grd, grids.zo, input_file_defs.zonfil, verbose_message)
        # grids.zo是numpy 数组，它代表着索引，因此它开始就要 - 1
        grids.zo = grids.zo.astype(np.int64)
        grids.zo[grids.zo > 0] -= 1
        info_message = (f"区域栅格\n"
                        f"{input_file_defs.zonfil}\t\t\t{sctr}栅格单元\n")
        verbose_message.message_request(info_message=info_message)
        if sctr != input_vars.imax or ncol != input_vars.col or nrow != input_vars.row:
            error_message = (f"TRIGRS主程序中的栅格不匹配：{input_file_defs.zonfil}\n"
                             f"请修正属性区域网格和/或初始化文件")
            verbose_message.message_request(error_message=error_message)
            raise ValueError(f"{error_message}")
    maxzo = np.max(grids.zo)
    if maxzo != input_vars.nzon - 1:
        error_message = (f"最大编号与属性栅格数量不相等\n"
                         f"修正属性栅格文件或初始化文件\n"
                         f"maxzo,nzon: {maxzo}, {input_vars.nzon}\n")
        verbose_message.message_request(error_message=error_message)
        raise ValueError(error_message)
    return sctr, ncol, nrow, header
