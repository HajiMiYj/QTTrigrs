import numpy as np


def dzero_brac(nstp, x):
    """
    Python版 dzero_brac，严格对应 Fortran 逻辑
    ----------
    输入：
        nstp : int
            步数（等于 len(x) - 1）
        x : array-like
            输入数据，长度应为 nstp+1
    输出：
        zroctr : int
            零点或符号变化的计数
        zrptr : ndarray[int]
            标记数组：
            0 = 无零点
            1 = 相邻符号变化（零交叉）
            2 = 节点值为零
    """
    x = np.asarray(x, dtype=np.float64)
    if len(x) != nstp + 1:
        raise ValueError(f"长度不匹配: len(x)={len(x)}, nstp+1={nstp + 1}")

    zrptr = np.zeros(nstp + 1, dtype=int)
    zroctr = 0
    tol = 1e-12  # 防止浮点精度误差，可选

    # 检查节点是否为零
    for n in range(nstp + 1):
        if abs(x[n]) < tol:
            zrptr[n] = 2
            zroctr += 1

    # 检查相邻符号变化
    for n in range(nstp):
        if x[n] * x[n + 1] < 0:
            zrptr[n] = 1  # 注意：Fortran写的是 zrptr(n)=1，对应 Python 下标 n
            zroctr += 1

    return zroctr, zrptr
