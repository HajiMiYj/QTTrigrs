import numpy as np


def irdswm(length, jmax, u, test, x, ctr, ulog):
    """
    将表示二维矩阵的整数值列表读取到两个一维数组中。其中一个数组是一个指针，用于跟踪矩阵中每一行的起始位置
    这种方案对于存储稀疏的“锯齿形”数组非常有利。这类数组具有不同长度的行，并且所有非零值都位于行的左侧。
    call irdswm(length = nwf ,
                jmax = imax,
                u = u(20),
                test = nodata,
                x = dsc,
                ctr = dsctr,
                ulog = u(19))
    :param length: x数组长度，注意len是python的关键词
    :param jmax: 最大行号
    :param u: 输入文件名（等价于Fortran的u）
    :param test: 行结束标记
    :param x: 预分配的一维数组（长度length）
    :param ctr: 预分配的指针数组（长度jmax+1）
    :param ulog: 日志文件对象
    """
    from .SparseRows import read_sparse_rows
    return read_sparse_rows(length, jmax, u, test, x, ctr, np.int64)
