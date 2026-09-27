import numpy as np


def srdgrd1(info):
    """
    根据 ssizgrd 返回的信息，生成 pf, cel, pf1 等数组。
    参数:
        info: dict, 来自 ssizgrd 的返回结果
    返回:
        pf1 : 列优先展平的原始数据（含 NODATA）
        pf  : 有效高程值数组（按列优先顺序）
        cel : 与 pf1 同长度的整数数组，有效单元为编号(1..n)，NODATA 为 0
    """
    data = np.ascontiguousarray(info['data'], dtype=np.float32)
    nodats = np.float32(info['nodat'])
    nrow = info['row']
    ncol = info['col']
    # 对应Fortran：i + (m-1)*ncol
    pf1 = data.reshape(-1, order='C')
    # 对应Fortran：temp(i) .ne. nodats
    valid_mask = pf1 != nodats
    ctr = int(np.count_nonzero(valid_mask))
    cel = np.zeros(pf1.size, dtype=np.int32)
    cel[valid_mask] = np.arange(1, ctr + 1, dtype=np.int32)

    # 布尔索引生成连续的float32一维数组
    pf = pf1[valid_mask]

    return {
        'pf1': pf1,
        'pf': pf,
        'cel': cel,
        'ctr': ctr,
        'nrow': nrow,
        'ncol': ncol,
        'celsiz': info['celsiz'],
        'nodat': info['nodat']
    }
