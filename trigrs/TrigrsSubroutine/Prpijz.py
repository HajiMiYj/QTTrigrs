import os

import numpy as np

from ..TrigrsModule.Grids import grids
from ..TrigrsModule.InputFileDefs import input_file_defs
from ..TrigrsModule.InputVars import input_vars
from ..TrigrsModule.ModelVars import model_vars


def prpijz(verbose_message, profil, ncol, nrow, header, vrsn):
    """
    注意，u(2)对应着outfil_files[0]，uijz(:)对应着outfil_files[]
    这里做统一接口
    """
    outfil_file = None
    outfil_files = []
    fini = ['Infinite', 'Finite']
    swt = 0
    if input_vars.nmax > 0:
        swt = 1
    # 1. 深度剖面文件 (flag >= -3 且 <= -1)
    if -3 <= input_vars.flag <= -1:
        outfil = os.path.join(input_file_defs.folder,
                              f"{profil}{input_file_defs.suffix}.txt")
        outfil_file = open(outfil, 'w')
        header = (f"每个单元格的深度剖面，TRIGRS，版本{vrsn}\n"
                  f"{fini[swt]}-深度 无流动 边界\n"
                  f"栅格数，坡角，步数#，时间\n")
        outfil_file.write(header)
        if input_vars.flag == -1:
            outfil_file.write(f"Z         P         FS\n")
        elif input_vars.flag == -2:
            outfil_file.write(f"Z         P      Pzero     Ptran      Pbeta       FS\n")
        else:
            if input_vars.unsat0:
                outfil_file.write("Z         P         FS      TH\n")
            else:
                outfil_file.write("Z         P         FS\n")
        outfil_files.append(outfil_file)

    if input_vars.flag in [-4, -5, -6]:
        if input_vars.deepz > 0:
            zval = input_vars.nzs + 3
        else:
            zval = input_vars.nzs + 2

        # 2. IJZ 格式文件 (flag = -4, -5, -6)
        profil = 'TR_ijz_p_th_'
        for j in range(input_vars.nout):
            # model_vars.uijz[j] = j + model_vars.uijz[0]
            file_num = j + 1
            stp = str(file_num)
            outfil = os.path.join(input_file_defs.folder,
                                  f"{profil}{input_file_defs.suffix}_{stp}.txt")
            outfil_file = open(outfil, 'w')
            header = (f"# 来自 TRIGRS 的准三维压力头数据，版本{vrsn}\n"
                      f"# {input_file_defs.title}\n")
            outfil_file.write(header)
            if input_vars.unsat0:
                outfil_file.write("# i  j  z  p  th\n")
            else:
                outfil_file.write("# i  j  z  p\n")
            header = (f"# 时间步= {input_vars.ksav[j]:12d}\n"
                      f"# 时间= {input_vars.tsav[j]:20.7g}\n"
                      "coords\n"
                      "ijz\n")
            outfil_file.write(header)

            outfil_files.append(outfil_file)

    if input_vars.flag <= -4:
        pf1 = np.asarray(grids.pf1).reshape((nrow, ncol))  # 保证二维
        test_mask = np.abs(pf1 - model_vars.test1) > 0.1  # True 表示有效单元
        # 得到所有有效单元的 i, j 坐标（Python 0基）
        jj_idx, ii_idx = np.where(test_mask)
        # 转换为 Fortran 1基（与原 Fortran 输出一致）
        ix = ii_idx + 1
        jy = nrow - jj_idx  # 左上角原点转左下角原点，且 1基
        # 存到 model_vars
        model_vars.ix = ix
        model_vars.jy = jy

    if -9 <= input_vars.flag <= -7:
        xllc = yllc = None
        for m in range(6):
            hstr = header[m].strip().lower()
            if hstr == 'xllcorner' or hstr == 'west:':
                xllc = model_vars.param[m]
            if hstr == 'yllcorner' or hstr == 'south:':
                yllc = model_vars.param[m]
        if xllc is None or yllc is None:
            raise ValueError("xllcorner/yllcorner not found in header.")
        #     pass
        #
        # if -9 <= input_vars.flag <= -7:
        profil = 'TR_xyz_p_th_'
        nvar = 5
        xmin = xllc
        xmax = xllc + float(ncol) * model_vars.celsiz
        ymin = yllc
        ymax = yllc + float(nrow) * model_vars.celsiz
        pmax = np.max(grids.zmax)
        plo = -pmax
        if input_vars.deepz > pmax:
            pmax = input_vars.deepz
        zlo = np.min(grids.elev) - pmax
        zhi = np.max(grids.elev)
        th_min = 0.0
        th_max = np.max(input_vars.ths)

        for j in range(input_vars.nout):
            stp = str(j + 1)
            outfil = os.path.join(input_file_defs.folder, f"{profil}{input_file_defs.suffix}_{stp}.okc")
            if input_vars.deepz > 0:
                outrow = grids.imax * (input_vars.nzs + 3)
            else:
                outrow = grids.imax * (input_vars.nzs + 2)
            try:
                with open(outfil, 'w') as f:
                    f.write(f"{nvar} {outrow} 12\n")
                    f.write("x\n")
                    f.write("y\n")
                    f.write("z\n")
                    f.write("p\n")
                    f.write("th\n")
                    f.write(f"{xmin:18.9g} {xmax:18.9g} 10\n")
                    f.write(f"{ymin:18.9g} {ymax:18.9g} 10\n")
                    f.write(f"{zlo:15.5g} {zhi:15.5g} 10\n")
                    f.write(f"{plo:11.4g} {pmax:11.4g} 10\n")
                    f.write(f"{th_min:11.4g} {th_max:11.4g} 10\n")
            except Exception as e:
                error_message = (f"无法打开或写入输出文件{outfil}\n"
                                 f"错误: {e}\n")
                verbose_message.message_request(error_message=error_message)
                raise IOError(error_message)
            outfil_files.append(outfil_file)
        pass
    return outfil_files
