import rasterio

from ..TrigrsModule.Grids import grids
from ..TrigrsModule.ModelVars import model_vars
from ..TrigrsSubroutine.Srdgrd import read_grid_head, fill_model_vars_param, read_grid_as_array


def irdgrd(grd, y, infil, verbose_message):
    """
    Python版irdgrd，兼容tif和asc，变量名对齐（栅格 IO 使用 rasterio）
    """
    ds = rasterio.open(infil)
    model_vars.nodat, ncol, nrow, xllcorner, yllcorner, model_vars.celsiz, band, header = read_grid_head(
        ds, infil, verbose_message)
    # param和header模拟Fortran头部
    if model_vars.nodat is None:
        model_vars.nodat = int(-9999)
    nodata = model_vars.nodat
    fill_model_vars_param(ncol, nrow, xllcorner, yllcorner, model_vars.celsiz, model_vars.nodat, model_vars.parami)
    ctr, y = read_grid_as_array(band, infil, ncol, nrow, grd, model_vars.nodat, y, grids.pf2, verbose_message)
    ds.close()
    return ctr, ncol, nrow, y, header, nodata, None
