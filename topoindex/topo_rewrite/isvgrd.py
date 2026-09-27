import os

import numpy as np
import rasterio

from ..topo_utils.append_log_message import append_log_messageV1


def isvgrd(
        z3,
        z2,
        reference_tif,
        output_file,
        nodat,
        log_buffer,
        main_app,
        output_nodata=-9999
):
    """
    使用 rasterio 将仅包含有效单元的一维整数数组恢复并写出为栅格。

    参数
    ----------
    z3 : numpy.ndarray  有效单元的一维整数结果数组
    z2 : numpy.ndarray  含 NoData 的完整二维参考数组，形状 (nrow, ncol)
    reference_tif : str 用于获取仿射变换和投影的参考栅格
    output_file : str   输出路径，仅支持 .tif/.tiff/.asc
    nodat : float       z2 中的 NoData 值
    log_buffer : io.StringIO
    main_app :          传给 append_log_message 的界面对象
    output_nodata : int 输出整数栅格的 NoData 值，默认 -9999

    返回
    -------
    str  输出栅格路径
    """
    z3 = np.asarray(z3, dtype=np.int32).reshape(-1)
    z2 = np.asarray(z2, dtype=np.float32)

    if z2.ndim != 2:
        error_message = f"z2必须是二维数组，当前维数为：{z2.ndim}"
        log_buffer.write(error_message + '\n')
        append_log_messageV1(main_app, 'Invalid reference grid array')
        raise ValueError(error_message)

    nrow, ncol = z2.shape
    nodat_f32 = np.float32(nodat)

    if np.isnan(nodat_f32):
        valid_mask = ~np.isnan(z2)
    else:
        valid_mask = np.abs(z2 - nodat_f32) > np.float32(0.1)

    valid_count = int(np.count_nonzero(valid_mask))

    if z3.size < valid_count:
        error_message = (f"结果数组长度不足：z3={z3.size}，"
                         f"有效单元数={valid_count}")
        log_buffer.write(error_message + '\n')
        append_log_messageV1(main_app, 'Invalid output grid data')
        raise ValueError(error_message)

    output_array = np.full((nrow, ncol), int(output_nodata), dtype=np.int32)
    output_array[valid_mask] = z3[:valid_count]

    log_buffer.write(f"Writing raster grid to: {output_file}\n")
    append_log_messageV1(main_app, 'Writing raster grid')

    # 读取参考栅格的仿射变换与投影
    try:
        with rasterio.open(reference_tif) as src:
            if src.width != ncol or src.height != nrow:
                error_message = ("The dimensions of z2 do not match the "
                                 f"reference raster: z2=({nrow}, {ncol})")
                log_buffer.write(error_message + '\n')
                append_log_messageV1(main_app, 'Raster dimensions do not match')
                raise ValueError(error_message)
            transform = src.transform
            crs = src.crs
    except ValueError:
        raise
    except Exception as exc:
        error_message = f"Unable to open reference raster: {reference_tif}"
        log_buffer.write(error_message + '\n')
        append_log_messageV1(main_app, 'Unable to open reference raster')
        raise RuntimeError(error_message) from exc

    extension = os.path.splitext(output_file)[1].lower()

    if extension == '.asc':
        driver = 'AAIGrid'
    elif extension in ('.tif', '.tiff'):
        driver = 'GTiff'
    else:
        error_message = f"Unsupported output raster format: {extension}"
        log_buffer.write(error_message + '\n')
        append_log_messageV1(main_app, 'Unsupported raster format')
        raise ValueError(error_message)

    profile = {
        'driver': driver,
        'height': nrow,
        'width': ncol,
        'count': 1,
        'dtype': 'int32',
        'transform': transform,
        'nodata': int(output_nodata),
    }
    if driver == 'GTiff':
        profile['crs'] = crs
        profile['compress'] = 'lzw'
        profile['tiled'] = True

    try:
        with rasterio.open(output_file, 'w', **profile) as dst:
            dst.write(output_array, 1)
    except Exception as exc:
        error_message = f"Unable to create raster: {output_file}\n原因：{exc}"
        log_buffer.write(error_message + '\n')
        append_log_messageV1(main_app, 'Unable to create raster')
        raise RuntimeError(error_message) from exc

    log_buffer.write(f"Raster grid saved successfully: {output_file}\n")
    append_log_messageV1(main_app, 'Raster grid saved successfully')

    return output_file
