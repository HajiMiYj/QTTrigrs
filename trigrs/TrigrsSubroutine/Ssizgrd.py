import os

import numpy as np
import rasterio

from ..TrigrsModule.ModelVars import model_vars


def ssizgrd(infil: str, verbose_message):
    """
    对应于ssizgrd.f95，兼容 tif 和 asc（栅格 IO 使用 rasterio）。
    :param infil: 栅格路径，允许 tif 和 asc
    :param verbose_message: 消息处理实例
    :return: (row, col, celsiz, nodat, ctr)
    """
    ext = os.path.splitext(infil)[1].lower()
    if ext not in ('.asc', '.tif', '.tiff'):
        error_message = (f"在子程序 ssizgrd 中打开输入文件时出错\n"
                         f"--> ,{infil}\n"
                         f"请检查文件名和位置")
        verbose_message.message_request(error_message=error_message)
        raise ValueError(f"不支持的文件类型: {error_message}")

    try:
        with rasterio.open(infil) as ds:
            col = ds.width
            row = ds.height
            model_vars.celsiz = abs(ds.transform.a)  # 像元宽度
            model_vars.nodat = ds.nodata
            data = ds.read(1)
            header = f"rasterio driver: {ds.driver}"
    except Exception as exc:
        error_message = (f"在子程序 ssizgrd 中打开输入文件时出错\n"
                         f"--> ,{infil}\n"
                         f"请检查文件名和位置\n原因：{exc}")
        verbose_message.message_request(error_message=error_message)
        raise ValueError(error_message)

    if model_vars.nodat is not None:
        ctr = int(((data != model_vars.nodat) & (~np.isnan(data.astype(np.float64)))).sum())
    else:
        ctr = int((~np.isnan(data.astype(np.float64))).sum())

    info_message = (f"{header}\n"
                    f"有效栅格数 = {ctr}\n"
                    f"总栅格数 = {row * col}\n")
    verbose_message.message_request(info_message=info_message)
    return int(row), int(col), float(model_vars.celsiz), float(model_vars.nodat), int(ctr)
