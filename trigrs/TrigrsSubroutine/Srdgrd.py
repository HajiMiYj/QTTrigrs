# call srdgrd(grd,col,ncol,nrow,celsiz,nodat,&
#   &slo,pf1,sctr,imax,temp,u(1),slofil,param,header,u(19))
# 重写srdgrd.f（栅格 IO 使用 rasterio）

import numpy as np
import rasterio

from ..TrigrsModule.Grids import grids
from ..TrigrsModule.InputVars import input_vars
from ..TrigrsModule.ModelVars import model_vars


def read_grid_head(ds, infil, verbose_message):
    if ds is None:
        error_message = (f"在srdgrd中打开输入文件时出现错误。\n"
                         f"--> {infil}\n"
                         f"请检查文件位置")
        verbose_message.message_request(error_message=error_message)
        raise ValueError(error_message)
    # 获取头部参数（rasterio DatasetReader）
    ncol = ds.width
    nrow = ds.height
    tr = ds.transform
    xllcorner = tr.c
    yllcorner = tr.f + nrow * tr.e if tr.e < 0 else tr.f
    celsiz = tr.a
    nodat = ds.nodata
    header = ['ncols', 'nrows', 'xllcorner', 'yllcorner', 'cellsize', 'NODATA_value']
    return nodat, ncol, nrow, xllcorner, yllcorner, celsiz, ds, header


def fill_model_vars_param(ncol, nrow, xllcorner, yllcorner, celsiz, nodat, param):
    param[0] = ncol
    param[1] = nrow
    param[2] = xllcorner
    param[3] = yllcorner
    param[4] = celsiz
    param[5] = nodat


def read_grid_as_array(band, infil, ncol, nrow, grd, nodat, pf, pf1, verbose_message):
    data = band.read(1)
    if data is None:
        raise ValueError(f"无法读取栅格：{infil}")
    flat = data.ravel()
    if flat.size > grd or flat.size > len(pf1):
        raise ValueError(f"栅格尺寸超出已分配范围：{infil}")
    mask = np.ones(flat.size, dtype=bool) if nodat is None else (
        ~np.isnan(flat) if np.isnan(nodat) else flat != nodat)
    count = int(np.count_nonzero(mask))
    if count > input_vars.imax or count > len(pf):
        raise ValueError(f"有效单元数量超出 grid_size.txt 中的 imax：{infil}")
    pf1[:flat.size] = flat
    pf[:count] = flat[mask]
    return count, pf


def srdgrd(grd, pf, infil, verbose_message):
    """
    读取一个 ASCII/GeoTIFF 栅格文件（如 DEM），将其数据读入一维数组，
    并统计有效数据单元格数量，同时处理无数据值和各种异常情况（对应 srdgrd.f）。

    返回：ctr, ncol, nrow, pf, header, ds
    """
    ds = rasterio.open(infil)
    model_vars.nodat, ncol, nrow, xllcorner, yllcorner, model_vars.celsiz, band, header = read_grid_head(
        ds, infil, verbose_message)
    if model_vars.nodat is None:
        model_vars.nodat = -9999.0
    fill_model_vars_param(ncol,
                          nrow,
                          xllcorner,
                          yllcorner,
                          model_vars.celsiz,
                          model_vars.nodat,
                          model_vars.param)
    # 读取数据
    ctr, pf = read_grid_as_array(band, infil, ncol, nrow, grd, model_vars.nodat, pf, grids.pf1, verbose_message)
    ds.close()
    return ctr, ncol, nrow, pf, header, None
