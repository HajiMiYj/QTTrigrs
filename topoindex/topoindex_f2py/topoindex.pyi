# topo_in_read.pyi
import numpy as np
from numpy.typing import NDArray

__version__: str

def topo_in_read(
    init_file: str,
) -> tuple[
    str,                    # title
    str,                    # heading
    int,                    # aif
    float,                  # pwr
    int,                    # itmax
    NDArray[np.int32],      # op, shape (6,)
    int,                    # lspars
    str,                    # suffix
    str,                    # folder
    str,                    # demfil
    str,                    # dirfil
    str,                    # logmsg
    int,                    # istatus
]: ...

def sindex(
    ra: NDArray[np.float32],
    n: int = ...,
) -> NDArray[np.int32]: ...

def correct_order(
    itmax: int,
    indx: NDArray[np.generic],
    lkup: NDArray[np.generic],
    cels: NDArray[np.generic],
    clcnt: int = ...,
) -> tuple[
    NDArray[np.generic],      # rndx
    NDArray[np.generic],      # ordr
    int,                    # cctr
    str,                    # logmsg
    int,                    # istatus
]: ...

def nxtcel(
    rc: int,
    prm: int,
    nodat: float,
    nodata: int,
    z: NDArray[np.generic],
    dir_grid: NDArray[np.generic],
    cell: NDArray[np.generic],
    save_list: int,
    list_file: str,
    nrow: int = ...,
    ncol: int = ...,
) -> tuple[
    NDArray[np.int32],      # cels
    int,                    # mmcnt
    str,                    # logmsg
    int,                    # istatus
]: ...

def slofac(
    z: NDArray[np.generic],
    celsiz: float,
    nodat: float,
    nodata: int,
    cel: NDArray[np.generic],
    dscfil: str,
    pwr: float,
    next_cells: NDArray[np.generic],
    wffil: str,
    dir_grid: NDArray[np.generic],
    spars: int,
    nrow: int = ...,
    ncol: int = ...,
    rc: int = ...,
) -> tuple[
    int,                    # dsctr
    NDArray[np.generic],      # ridge
    str,                    # logmsg
    int,                    # istatus
]: ...


def write_index_list(
    rndx: NDArray[np.generic],
    outfil: str,
    clcnt: int = ...
) -> int:
    """
    使用Fortran循环写出单元编号与索引列表。

    Parameters
    ----------
    rndx
        一维整数索引数组。
    outfil
        输出文本文件路径。
    clcnt
        要写出的数组元素数量，默认由rndx长度推断。

    Returns
    -------
    int
        状态码：0表示成功，1表示文件打开失败。
    """
    ...