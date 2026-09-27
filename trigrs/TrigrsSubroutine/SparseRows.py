import warnings

import numpy as np


def read_sparse_rows(length, jmax, path, marker, values, pointers, dtype):
    """Read TopoIndex marker/row/value records in O(tokens) time.

    Both readers return one-based row pointers, as in the source format.
    Avoid Python scalar lists and repeated prefix sums on multi-million-cell grids.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        # Buffered parsing is much faster than token-by-token fromfile on Windows.
        chunks = []
        with open(path, "rb") as stream:
            while block := stream.read(4 * 1024 * 1024):
                block += stream.readline()  # Never cut a numeric token in half.
                chunks.append(np.fromstring(block, dtype=dtype, sep=" "))
        data = np.concatenate(chunks) if chunks else np.empty(0, dtype=dtype)
        del chunks
    starts = np.flatnonzero(data == marker)
    if (len(starts) != jmax or not len(starts) or starts[0] != 0
            or starts[-1] + 1 >= len(data)):
        raise ValueError(f"稀疏列表行数/结束标记错误：{path}，预期 {jmax} 行")
    if np.any(np.diff(starts) < 2):
        raise ValueError(f"稀疏列表缺少行号：{path}")
    if not np.array_equal(data[starts + 1], np.arange(1, jmax + 1)):
        raise ValueError(f"稀疏列表行号必须从 1 连续递增：{path}")
    count = len(data) - 2 * jmax
    if count > length:
        raise ValueError(f"稀疏列表超出 nwf：{path}，需要 {count}，已分配 {length}")
    keep = np.ones(len(data), dtype=bool)
    keep[starts] = False
    keep[starts + 1] = False
    values[:count] = data[keep]
    pointers[:jmax] = starts - 2 * np.arange(jmax) + 1
    pointers[jmax] = count + 1
    return values
