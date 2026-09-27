import numpy as np

from ..TrigrsModule.Grids import grids
from ..TrigrsModule.InputVars import input_vars
from ..TrigrsModule.ModelVars import model_vars
from ..TrigrsSubroutine.DzeroBrac import dzero_brac


def _write_ijz_line(fobj, ix: int, jy: int, z: float, p: float, th: float):
    # 近似 Fortran '(2(i6,1x), g15.5, 1x, 2(g11.4,1x))'
    fobj.write(f"{ix:6d} {jy:6d} {z:15.5g} {p:11.4g} {th:11.4g}\n")


def svijz(i, jf, delh, newdep, verbose_message, ijz_files, dcf_i, beta_i, p0zmx_i):
    """
    Python 版 svijz（与 Fortran 逐条对应）
    参数:
      i: 0基单元索引
      jf: 0基时间索引
      delh, newdep: 上层过程传入
      verbose_message: 需有 message_request(error_message=...) 方法
      ijz_files: 长度为 nout 的已打开文件对象列表(IOTextWrapper)
    说明:
      - 使用全局 model_vars.p, model_vars.thz 作为当前剖面的 p, thz（长度 nzs+1, 索引 0..nzs）
      - wtab 写入索引为 i + jf*imax
    """
    imax = input_vars.imax
    nzs = int(input_vars.nzs)            # 节点数为 nzs+1（0..nzs）
    zmin = float(input_vars.zmin)

    elev_i = grids.elev[i]
    depth_i = grids.depth[i]
    zmax_i = grids.zmax[i]
    zo_i = grids.zo[i]

    # 边界与初值
    zbot = elev_i - zmax_i
    ztop = elev_i - zmin
    zwat0 = elev_i - depth_i
    zwat = np.full(nzs + 1, zwat0, dtype=np.float64)  # 节点处水位标高
    wtptr = np.zeros(nzs + 1, dtype=np.int32)         # 0: 无, 1: 区间零点, 2: 节点零点
    wptr = np.zeros(nzs + 1, dtype=np.int32)          # 记录每个水位对应的“节点索引”
    wtctr = 0
    # wctr = 0

    # 深层点
    ldeep = True
    zdeep = elev_i - input_vars.deepz
    if zdeep > ztop:
        ldeep = False
    if zdeep > zbot and ldeep:
        zdeep = zbot - zmax_i

    zns = float(nzs)
    zinc = (zmax_i - zmin) / zns if zns > 0.0 else 0.0

    # 当前剖面 p, thz（长度 nzs+1）
    p = model_vars.p
    thz = model_vars.thz

    ptop = p[0]
    pbot = p[nzs]

    # p>=0 的节点设为饱和含水率（对应 Fortran do nw=1..nzs+1）
    for nw in range(nzs + 1):
        if p[nw] >= 0.0:
            thz[nw] = input_vars.ths[zo_i]

    th_top = thz[0]
    th_bot = thz[nzs]
    th_deep = input_vars.ths[zo_i]

    # 估计水位（非饱和 or 饱和）
    if dcf_i > 0.0 and (input_vars.unsat[zo_i] or input_vars.igcap[zo_i]):
        if grids.rikzero[i] >= 0.0:
            dusz = depth_i - 1.0 / input_vars.alp[zo_i]  # 与 Fortran 一致
            zwat[0] = elev_i - (dusz - delh)
        else:
            zwat[0] = elev_i - newdep
        wtctr = 1
        wtptr[0] = 1
        wptr[0] = 0
    elif dcf_i <= 0.0:
        # 饱和：找零点
        zroctr, zrptr = dzero_brac(nzs, p)  # 你实现的版本返回 (zroctr, zrptr)
        wtptr[:] = zrptr
        wtctr = int(zroctr)
        thz[:] = input_vars.ths[zo_i]
        wctr = 0
        dwat = 0.0
        for nw in range(nzs + 1):
            if wtptr[nw] > 0:
                if wtptr[nw] == 2:
                    # 水位在节点
                    wctr += 1
                    z = zmin + zinc * float(nw)        # Fortran: nw-1（1基） => 这里用 0基的 nw
                    dwat = z
                if wtptr[nw] == 1 and nw < nzs:
                    # 水位在区间
                    wctr += 1
                    z = zmin + zinc * float(nw)
                    dwat = z + zinc * (0.0 - p[nw]) / (p[nw + 1] - p[nw])
                if grids.rikzero[i] >= 0.0:
                    zwat[nw] = elev_i - dwat
                    wptr[wctr - 1] = nw
                else:
                    zwat[nw] = elev_i - newdep
                    wptr[wctr - 1] = nw
            if wctr == wtctr:
                break
        # 底部仍为负压：水位在底界下（Fortran 近似公式）
        if p[nzs] < 0.0:
            wtptr[nzs] = 1
            wtctr += 1
            wctr += 1
            zwat[nzs] = elev_i - depth_i + beta_i * (p[nzs] - p0zmx_i)
            if zwat[nzs] < (elev_i - depth_i):
                zwat[nzs] = elev_i - depth_i
            wptr[wtctr - 1] = nzs


    # 写 wtab（仅 outp(1)）
    if input_vars.outp[0]:
        if wtctr == 0:
            if p[0] > 0.0 and zmin >= 0.0:
                wtctr = wtctr + 1
                # wctr = wctr + 1
                wptr[0] = 0
                zwat[0] = elev_i
                p[0] = 0.0
            else:
                verbose_message.message_request(
                    error_message=f"Error in svijz(): wtctr not initialized at cell {i}"
                )
        # 使用最低水位
        idx = wptr[wtctr - 1] if wtctr > 0 else 0
        kind = input_vars.el_or_dep.strip().lower()
        if kind == 'eleva':
            wtab_temp = zwat[idx]
            if wtab_temp < 0.0:
                wtab_temp = elev_i
            if jf == 0:
                wtab_temp = elev_i - depth_i
            grids.wtab[i + jf * imax] = wtab_temp
        elif kind == 'depth':
            wtab_temp = elev_i - zwat[idx]
            if wtab_temp < 0.0:
                wtab_temp = 0.0
            if jf == 0:
                wtab_temp = depth_i
            grids.wtab[i + jf * imax] = wtab_temp
        else:
            wtab_temp = zwat[idx]
            if wtab_temp < 0.0:
                wtab_temp = elev_i
            if jf == 0:
                wtab_temp = elev_i - depth_i
            grids.wtab[i + jf * imax] = wtab_temp





    # 仅当 flag ∈ [-7, -4] 写 ijz
    if input_vars.flag > -4 or input_vars.flag < -7:
        return

    # 深层点压力（SCOOPS）
    dw = input_vars.deepwat.strip().lower()
    if dw == 'zero':
        pdeep = 0.0
    elif dw == 'flow':
        pdeep = beta_i * (elev_i - depth_i - zdeep)
    elif dw == 'hydr':
        pdeep = (elev_i - depth_i - zdeep)
    elif dw == 'relh':
        relhgt = (elev_i - model_vars.zmn[0]) / (model_vars.zmx[0] - model_vars.zmn[0])
        pdeep = (elev_i - depth_i - zdeep) * (1.0 - relhgt / 3.0)
    else:
        pdeep = 0.0

    # 保存 ijz（全量或抽稀）
    fobj = ijz_files[jf]  # 已打开 IOTextWrapper
    ix = model_vars.ix[i]
    jy = model_vars.jy[i]

    if input_vars.flag in (-4, -5):
        if input_vars.spcg < 1:
            input_vars.spcg = 1
        dinc = 1 if input_vars.flag == -4 else input_vars.spcg
        fdinc = float(dinc)
        z = ztop

        if dcf_i > 0.0 and input_vars.unsat[zo_i]:
            # 非饱和
            for m in range(0, nzs + 1, dinc):
                _write_ijz_line(fobj, ix, jy, z, p[m], thz[m])
                if (zwat[0] < z) and (zwat[0] > (z - fdinc * zinc)) and (p[m] < 0.0):
                    if zwat[0] > (zbot * 1.00001):
                        _write_ijz_line(fobj, ix, jy, float(zwat[0]), 0.0, input_vars.ths[zo_i])
                z -= (zinc * fdinc)
            if zwat[0] < (zbot / 1.00001):
                _write_ijz_line(fobj, ix, jy, float(zwat[0]), 0.0, input_vars.ths[zo_i])
            if ldeep:
                _write_ijz_line(fobj, ix, jy, zdeep, pdeep, th_deep)

        elif dcf_i <= 0.0:
            # 饱和
            for m in range(0, nzs + 1, dinc):
                _write_ijz_line(fobj, ix, jy, z, p[m], thz[m])
                if dinc == 1:
                    if wtptr[m] == 1:
                        _write_ijz_line(fobj, ix, jy, float(zwat[m]), 0.0, input_vars.ths[zo_i])
                elif dinc > 1:
                    for m1 in range(m, min(m + dinc, nzs + 1)):
                        if wtptr[m1] == 1:
                            _write_ijz_line(fobj, ix, jy, float(zwat[m1]), 0.0, input_vars.ths[zo_i])
                z -= (zinc * fdinc)
            if ldeep:
                _write_ijz_line(fobj, ix, jy, zdeep, pdeep, th_deep)

    if input_vars.flag == -6:
        # 稀疏输出
        lopmn = False
        lopmx = False
        loxlo = False
        plin = np.zeros(nzs + 1, dtype=np.float64)
        rp = np.zeros(nzs + 1, dtype=np.float64)
        mp = ptop / (ztop - zwat[nzs])  # Fortran: zwat(nzs+1)
        z = ztop
        plin[0] = ptop
        # 注意：与 Fortran 一致，循环到出现 z < zwat(1) 才提前退出（非饱和）
        for m in range(1, nzs + 1):
            z -= zinc
            if (z < zwat[0]) and (dcf_i > 0.0) and input_vars.unsat[zo_i]:
                break
            plin[m] = ptop - mp * (ztop - z)
            rp[m] = p[m] - plin[m]

        rpmin = np.min(rp)
        mrpn = int(np.argmin(rp))      # 0基
        rpmax = np.max(rp)
        mrpx = int(np.argmax(rp))      # 0基
        tol1 = abs(p[mrpn] / 100.0)
        tol2 = abs(p[mrpx] / 100.0)
        # 非饱和分支里，Fortran 用 zrpn = ztop - zinc*(mrpn(1)-1)
        zrpn = ztop - zinc * float(mrpn)      # 0基 -> 与 (mrpn(1)-1) 等价
        zrpx = ztop - zinc * float(mrpx)

        if (abs(rpmin) >= tol1) and (rpmin < 0.0) and (zrpn > zwat[0]):
            lopmn = True
        if (abs(rpmax) >= tol2) and (rpmax > 0.0) and (zrpx > zwat[0]):
            lopmx = True

        # 下面 mfrst/mlast 使用 1基逻辑，在写饱和分支时需注意 Fortran 的 -1 差异
        mfrst = mrpn + 1
        mlast = mrpx + 1
        if mrpn > mrpx:
            loxlo = True
            mfrst = mrpx + 1
            mlast = mrpn + 1

        if dcf_i > 0.0 and input_vars.unsat[zo_i]:
            # 非饱和：顶/底与插值坐标按 zrpn/zrpx 写
            _write_ijz_line(fobj, ix, jy, ztop, ptop, th_top)
            if loxlo:
                if lopmx and (mrpx + 1 > 1) and (mrpx + 1 < (nzs + 1)):
                    _write_ijz_line(fobj, ix, jy, zrpx, p[mrpx], thz[mrpx])
                if lopmn and (mrpn + 1 > 1) and (mrpn + 1 < (nzs + 1)):
                    _write_ijz_line(fobj, ix, jy, zrpn, p[mrpn], thz[mrpn])
            else:
                if lopmn and (mrpn + 1 > 1) and (mrpn + 1 < (nzs + 1)):
                    _write_ijz_line(fobj, ix, jy, zrpn, p[mrpn], thz[mrpn])
                if lopmx and (mrpx + 1 > 1) and (mrpx + 1 < (nzs + 1)):
                    _write_ijz_line(fobj, ix, jy, zrpx, p[mrpx], thz[mrpx])
            if (zwat[0] < ztop) and (ptop < 0.0):
                if zwat[0] > (zbot * 1.00001):
                    _write_ijz_line(fobj, ix, jy, float(zwat[0]), 0.0, input_vars.ths[zo_i])
            _write_ijz_line(fobj, ix, jy, zbot, pbot, th_bot)
            if zwat[nzs] < (zbot / 1.00001):
                _write_ijz_line(fobj, ix, jy, float(zwat[nzs]), 0.0, input_vars.ths[zo_i])
            if ldeep:
                _write_ijz_line(fobj, ix, jy, zdeep, pdeep, th_deep)

        elif dcf_i <= 0.0:
            # 饱和：注意 Fortran 这里使用 ztop - zinc*float(mrpx(1))（1基），因此 0基要用 (mrpx+1)
            _write_ijz_line(fobj, ix, jy, ztop, ptop, 1.0)
            if loxlo:
                if lopmx and (mrpx + 1 > 1) and (mrpx + 1 < (nzs + 1)):
                    _write_ijz_line(fobj, ix, jy, ztop - zinc * float(mrpx + 1), p[mrpx], thz[mrpx])
                # 检查 min/max 之间的水位（Fortran: do m=mfrst, mlast-1）
                for m in range(mfrst, mlast):
                    m0 = m - 1  # 转 0基
                    if m0 < (nzs + 1) and (wtptr[m0] == 1 or wtptr[m0] == 2):
                        _write_ijz_line(fobj, ix, jy, float(zwat[m0]), 0.0, input_vars.ths[zo_i])
                if lopmn and (mrpn + 1 > 1) and (mrpn + 1 < (nzs + 1)):
                    _write_ijz_line(fobj, ix, jy, ztop - zinc * float(mrpn + 1), p[mrpn], thz[mrpn])
            else:
                if lopmn and (mrpn + 1 > 1) and (mrpn + 1 < (nzs + 1)):
                    _write_ijz_line(fobj, ix, jy, ztop - zinc * float(mrpn + 1), p[mrpn], thz[mrpn])
                for m in range(mfrst, mlast):
                    m0 = m - 1
                    if m0 < (nzs + 1) and (wtptr[m0] == 1 or wtptr[m0] == 2):
                        _write_ijz_line(fobj, ix, jy, float(zwat[m0]), 0.0, input_vars.ths[zo_i])
                if lopmx and (mrpx + 1 > 1) and (mrpx + 1 < (nzs + 1)):
                    _write_ijz_line(fobj, ix, jy, ztop - zinc * float(mrpx + 1), p[mrpx], thz[mrpx])
            # 查找更低的水位（Fortran: do m=mlast, nzs）
            for m in range(mlast, nzs + 1):
                m0 = m - 1
                if wtptr[m0] == 1 or wtptr[m0] == 2:
                    if zwat[m0] > (zbot * 1.00001):
                        _write_ijz_line(fobj, ix, jy, float(zwat[m0]), 0.0, input_vars.ths[zo_i])
            _write_ijz_line(fobj, ix, jy, zbot, pbot, 1.0)
            if zwat[nzs] < (zbot / 1.00001):
                _write_ijz_line(fobj, ix, jy, float(zwat[nzs]), 0.0, input_vars.ths[zo_i])
            if ldeep:
                _write_ijz_line(fobj, ix, jy, zdeep, pdeep, th_deep)
