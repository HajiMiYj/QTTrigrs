import numpy as np

from .SparseRows import read_sparse_rows


def srdswm(length, jmax, u, test, x, ctr, ulog):
    return read_sparse_rows(length, jmax, u, test, x, ctr, np.float64)
