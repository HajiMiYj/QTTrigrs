import numpy as np
import rasterio


def rdflodir(direc):
    """
    读取流向栅格文件，返回列优先展平的一维整数数组及相关信息。
    对应 Fortran 子程序 rdflodir（栅格 IO 使用 rasterio）。

    参数:
        direc : str, 流向文件路径

    返回:
        dict, 包含:
            'dir'   : 一维 NumPy 数组 (dtype=int32)，按列优先展平的流向值
            'nrow'  : 行数
            'ncol'  : 列数
            'nodat' : NODATA 值（从文件头读取，若无则为默认 -9999）
            'geotransform': 仿射变换六元组（兼容旧调用方）
            'projection': 投影 WKT
            'mnd'   : None
    """
    with rasterio.open(direc) as ds:
        ncol = ds.width
        nrow = ds.height
        nodat = ds.nodata
        if nodat is None:
            nodat = -9999

        tr = ds.transform
        geotransform = (tr.c, tr.a, tr.b, tr.f, tr.d, tr.e)
        projection = ds.crs.to_wkt() if ds.crs else ''
        data = ds.read(1).astype(np.int32)

    dir_flat = np.asfortranarray(data.flatten(order='F'))

    return {
        'dir': dir_flat,
        'nrow': nrow,
        'ncol': ncol,
        'nodat': nodat,
        'geotransform': geotransform,
        'projection': projection,
        'mnd': None
    }
