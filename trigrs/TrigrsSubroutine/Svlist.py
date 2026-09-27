import math
import numpy as np

from run_control import yield_

from ..TrigrsModule.Grids import grids
from ..TrigrsModule.InputVars import input_vars
from ..TrigrsModule.ModelVars import model_vars


def _listing_cells(count, stop_event=None):
    print(f"正在写入逐深度详细列表，共 {count:,} 个单元（大量文本输出可能需要较长时间）", flush=True)
    for i in range(count):
        if i % 25000 == 0:
            yield_(stop_event)
        yield i
        if (i + 1) % 250000 == 0 or i + 1 == count:
            print(f"详细列表写入 {i + 1:,}/{count:,} ({(i + 1)/count:.0%})", flush=True)


def svlist(u1, stop_event=None):
    try:
        # 常量与变量
        pi = getattr(model_vars, "pi", math.pi)
        ddg2rad = pi / 180.0

        imax = int(input_vars.imax)
        nout = int(input_vars.nout)
        nzs = int(input_vars.nzs)
        zmin = float(input_vars.zmin)
        flag = int(input_vars.flag)

        # tsav 兼容获取
        if hasattr(input_vars, "tsav"):
            tsav_arr = input_vars.tsav
        elif hasattr(model_vars, "tsav"):
            tsav_arr = model_vars.tsav
        elif hasattr(model_vars, "qtime"):
            tsav_arr = model_vars.qtime
        else:
            tsav_arr = np.zeros(nout, dtype=float)

        # 分支 -1：简单列表（z, p3d, fs3d）
        if flag == -1:
            for i in _listing_cells(imax, stop_event):
                rslo = float(grids.slo[i])
                for n in range(nout):
                    i1 = i + 1
                    n1 = n + 1
                    u1.write(f"cell {i1:12d}{(rslo / ddg2rad):6.1f}{n1:12d}  {float(tsav_arr[n]):.8g}\n")
                    zns = float(nzs)
                    z = zmin
                    zinc = (float(grids.zmax[i]) - zmin) / zns if zns > 0.0 else 0.0
                    base = i + n * imax
                    for j in range(nzs + 1):
                        p_val = float(model_vars.p3d[base, j])
                        fs_val = float(model_vars.fs3d[base, j])
                        u1.write(f"{z:12.5g} {p_val:12.5g} {fs_val:12.5g}\n")
                        z += zinc

        # 分支 -2：详细列表（z, p3d, pzero3d, ptran3d, bline, fs3d）
        elif flag == -2:
            flowdir = str(getattr(input_vars, "flowdir", "")).strip().lower()
            for i in _listing_cells(imax, stop_event):
                rslo = float(grids.slo[i])
                b1 = math.cos(rslo)
                # 计算 beta（Iverson beta线）
                if flowdir == "slope":
                    beta = b1 * b1
                elif flowdir == "hydro":
                    beta = 1.0
                else:
                    beta = b1 * b1 - float(grids.rikzero[i])
                if abs(b1 - float(grids.rikzero[i])) < 1.0e-6:
                    beta = 0.0

                for n in range(nout):
                    i1 = i + 1
                    n1 = n + 1
                    u1.write(f"cell {i1:12d}{(rslo / ddg2rad):6.1f}{n1:12d}  {float(tsav_arr[n]):.8g}\n")
                    zns = float(nzs)
                    z = zmin
                    zinc = (float(grids.zmax[i]) - zmin) / zns if zns > 0.0 else 0.0
                    base = i + n * imax
                    for j in range(nzs + 1):
                        bline_val = z * beta
                        # 若需要，也把 bline 写回全局（与 Fortran bline(j)=... 一致）
                        try:
                            model_vars.bline[j] = bline_val
                        except Exception as e:
                            print(e)
                            pass
                        p_val = float(model_vars.p3d[base, j])
                        pzero_val = float(model_vars.pzero3d[i, j])
                        ptran_val = float(model_vars.ptran3d[base, j])
                        fs_val = float(model_vars.fs3d[base, j])
                        u1.write(
                            f"{z:12.5g} {p_val:12.5g} {pzero_val:12.5g} {ptran_val:12.5g} {bline_val:12.5g} {fs_val:12.5g}\n"
                        )
                        z += zinc

        # 分支 -3：水压头+安全系数(+含水率)
        elif flag == -3:
            unsat0 = bool(getattr(input_vars, "unsat0", False))
            for i in _listing_cells(imax, stop_event):
                rslo = float(grids.slo[i])
                for n in range(nout):
                    i1 = i + 1
                    n1 = n + 1
                    u1.write(f"cell {i1:12d}{(rslo / ddg2rad):6.1f}{n1:12d}  {float(tsav_arr[n]):.8g}\n")
                    zns = float(nzs)
                    z = zmin
                    zinc = (float(grids.zmax[i]) - zmin) / zns if zns > 0.0 else 0.0
                    base = i + n * imax
                    if unsat0:
                        for j in range(nzs + 1):
                            p_val = float(model_vars.p3d[base, j])
                            fs_val = float(model_vars.fs3d[base, j])
                            th_val = float(model_vars.th3d[base, j])
                            u1.write(f"{z:12.5g} {p_val:12.5g} {fs_val:12.5g} {th_val:12.5g}\n")
                            z += zinc
                    else:
                        for j in range(nzs + 1):
                            p_val = float(model_vars.p3d[base, j])
                            fs_val = float(model_vars.fs3d[base, j])
                            u1.write(f"{z:12.5g} {p_val:12.5g} {fs_val:12.5g}\n")
                            z += zinc
        # 其它 flag：与 Fortran 相同，不输出
        else:
            return
    finally:
        # if need_close:
        u1.close()
