import numpy as np
import rasterio


def ssizgrd(infil):
    """
    读取栅格文件（如 DEM），获取行列数、单元大小、NODATA 值，
    并统计有效数据单元数（非 NODATA）。对应 Fortran 子程序 ssizgrd。
    （栅格 IO 使用 rasterio）

    返回:
        dict: row, col, celsiz, nodat, ctr, ctall, data, geotransform, projection
    """
    with rasterio.open(infil) as ds:
        col = ds.width
        row = ds.height
        tr = ds.transform
        celsiz = abs(tr.a)
        nodat = ds.nodata
        if nodat is None:
            nodat = -9999.0
        data = ds.read(1).astype(np.float32)
        geotransform = (tr.c, tr.a, tr.b, tr.f, tr.d, tr.e)
        projection = ds.crs.to_wkt() if ds.crs else ''

    if nodat is not None:
        valid_mask = (data != nodat)
        ctr = int(np.count_nonzero(valid_mask))
    else:
        ctr = data.size

    ctall = data.size

    return {
        'row': row,
        'col': col,
        'celsiz': celsiz,
        'nodat': nodat,
        'ctr': ctr,
        'ctall': ctall,
        'data': data,
        'geotransform': geotransform,
        'projection': projection
    }
