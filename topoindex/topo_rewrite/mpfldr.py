import numpy as np


def mpfldr(dir_flat, nodata):
    """
    将 ESRI Arc/Grid 流向编码转换为 TopoIndex/TRIGRS 流向编码。
    对应 Fortran 子程序 mpfldr。

    参数：
        dir_flat    : numpy 数组（整数），流向值，将被原地修改
        nodata : 整数，NODATA 值，这些位置保持不变

    返回：
        dir_flat    : 修改后的数组（原地修改，同时返回）
    """
    dir_flat = np.asarray(dir_flat, dtype=np.int32)

    # 创建查找表，长度 256，默认值为 5（未定义流向指向自身）
    adr = np.full(256, 5, dtype=np.int32)

    # 设置 ESRI -> TopoIndex 映射
    adr[32] = 1
    adr[64] = 2
    adr[128] = 3
    adr[16] = 4
    adr[1] = 6
    adr[8] = 7
    adr[4] = 8
    adr[2] = 9

    # 仅对非 NODATA 单元进行替换
    mask = (dir_flat != nodata)
    dir_flat[mask] = adr[dir_flat[mask]]

    return dir_flat
