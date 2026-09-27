import os

import numpy as np
import rasterio
from rasterio.transform import from_origin

from ..TrigrsModule.Grids import grids
from ..TrigrsModule.InputFileDefs import input_file_defs


def ssvgrd(z3, z2, nrow, ncol, nodata, param, u1, outfil):
    """
    将一维有效数据 z3 按照模板 z2 的位置，写入二维栅格文件（.asc 或 .tif）。

    :param z3: 一维有效数据（长度 = 有效单元数）
    :param z2: 模板数组（长度 grd），有效位置写 z3，其余写 nodata
    :param nrow: 行
    :param ncol: 列数
    :param nodata: nodata 值
    :param param: [ncol, nrow, xllcorner, yllcorner, cellsize, NODATA_value]
    :param u1: 日志文件对象
    :param outfil: 输出文件名（字符串）
    """
    if grids.grxt == '.asc':
        driver_name = 'AAIGrid'
    elif grids.grxt == '.tif':
        driver_name = 'GTiff'
    else:
        driver_name = 'GTiff'

    # 1. 创建输出数组，默认填充 nodata
    grid = np.full_like(z2, nodata, dtype=np.float32)
    mask = (z2 != nodata)
    if int(np.count_nonzero(mask)) != len(z3):
        raise ValueError(f"有效数据数量 {len(z3)} 与模板 {int(np.count_nonzero(mask))} 不匹配")
    grid[mask] = z3  # 只填充有效值，nodata 保留
    grid2_d = grid.reshape((nrow, ncol))

    # 2. 仿射变换：xllcorner/yllcorner 是左下角，rasterio 需要左上角
    xllcorner, yllcorner, cellsize = param[2], param[3], param[4]
    transform = from_origin(xllcorner, yllcorner + nrow * cellsize, cellsize, cellsize)

    # 3. 写出栅格，先确保目录存在
    out_dir = os.path.dirname(str(outfil))
    if out_dir and not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError:
            pass

    try:
        crs = None
        if input_file_defs.elevfil:
            try:
                with rasterio.open(input_file_defs.elevfil) as src:
                    crs = src.crs
            except Exception:
                crs = None
        profile = {
            'driver': driver_name,
            'height': nrow,
            'width': ncol,
            'count': 1,
            'dtype': 'float32',
            'crs': crs,
            'transform': transform,
            'nodata': float(nodata),
        }
        with rasterio.open(outfil, 'w', **profile) as dst:
            dst.write(grid2_d.astype(np.float32), 1)
    except Exception as exc:
        error_message = (f"在ssvgrd打开输出文件时出错\n"
                         f"--> {outfil}\n"
                         f"请检查文件名和文件状态\n"
                         f"原因：{exc}\n")
        print(error_message)
        u1.write(error_message)
        raise RuntimeError('-20 in ssvgrd()') from exc
