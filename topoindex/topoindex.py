import io
import os
from datetime import datetime
import numpy as np
from run_control import yield_
from .topo_utils.append_log_message import append_log_messageV1, append_log_messageV2
from .topo_utils.error_handle import handle_tpindx_error
from .topo_rewrite.isvgrd import isvgrd
from .topo_rewrite.mpfldr import mpfldr
from .topo_rewrite.rdflodir import rdflodir
from .topo_rewrite.srdgrd1 import srdgrd1
from .topo_rewrite.ssizgrd import ssizgrd
from .topoindex_f2py import topoindex
from .TopoIndexInputFile import fortran_path, from_fortran_text, parse_annotations

#: 栅格产物只允许这两种格式。绝不使用 .txt：
#: 没有扩展名约定的纯 ASCII 网格不是合法栅格，GIS 也打不开。
#: 与 TRIGRS 的 lasc 约定保持一致：T -> .asc，F -> .tif。
RASTER_EXT_ASC = ".asc"
RASTER_EXT_TIF = ".tif"


def raster_ext(lasc: bool | None = None) -> str:
    """
    返回 TopoIndex 栅格产物应使用的扩展名。

    :param lasc: 与 TRIGRS 的 lasc 含义一致，True -> .asc，False -> .tif。
                 None 时从环境变量 TRIGRS_RASTER_EXT 读取（asc/tif），
                 默认 .asc。
    """
    if lasc is None:
        choice = os.environ.get("TRIGRS_RASTER_EXT", "asc").strip().lower()
        lasc = choice not in ("tif", "tiff")
    return RASTER_EXT_ASC if lasc else RASTER_EXT_TIF


def dec(s: bytes | str) -> str:
    """
    把 Fortran 回传的字符内容解码成字符串。

    Fortran 用的是系统 ANSI 代码页，直接按 UTF-8 解码中文路径会变成乱码，
    因此统一走 :func:`from_fortran_text`。
    """
    return from_fortran_text(s)


def topoindex_main(main_app, init_file, stop_event=None, output_folder=None):
    """
    :param stop_event: 可选 threading.Event，置位后中断写栅格阶段。
    :param output_folder: 可选输出目录；给定时覆盖 DEM 所在目录。

    Fortran日志的写法：
    use log_utils, only: reset_log, add_log, get_log
    :reset_log()  ! 重置日志缓冲区
    add_log('Some log message')  ! 添加日志信息
    get_log(logmsg)  ! 获取日志信息到 logmsg

    python侧日志的写法：
    log_buffer = io.StringIO() # 创建日志缓冲区
    把Fortran日志写入log_buffer
    如果python侧自己要追加，则log_buffer.write(f"str")
    """
    opthfil = 'TIdsneiList_'
    celfil = 'TIdscelGrid_'
    ndxfil = 'TIcelindxGrid_'
    ndxlst = 'TIcelindxList_'
    drofil = 'TIflodirGrid_'
    dscfil = 'TIdscelList_'
    wffil = 'TIwfactorList_'
    sizfil = 'TIgrid_size'
    rdgfil = 'TIridge_crest_'
    # 栅格产物统一用 .asc / .tif（见 raster_ext）：绝不写 .txt
    with open(init_file, encoding="utf-8", errors="replace") as handle:
        saved_format = parse_annotations(handle.read()).get("topo_raster_ext", "asc")
    rext = raster_ext() if "TRIGRS_RASTER_EXT" in os.environ else raster_ext(saved_format != "tif")
    log_buffer = io.StringIO()
    init_dir = os.path.dirname(init_file)
    (title, heading, aif, pwr, itmax, op, lspars, suffix, folder,
     demfil, dirfil, logmsg, istatus) = topoindex.topo_in_read(fortran_path(init_file))

    vdate = '11May2015'
    vrsn = '1.0.14'
    append_log_messageV1(main_app, "TopoIndex: Topographic Indexing and")
    append_log_messageV1(main_app, " flow distribution factors for routing")
    append_log_messageV1(main_app, " runoff through Digital Elevation Models")
    append_log_messageV1(main_app, "            By Rex L. Baum")
    append_log_messageV1(main_app, "       U.S. Geological Survey")
    append_log_messageV1(main_app, "       & Jbc, NanChang University")
    append_log_messageV1(main_app, f"    Python Version {vrsn}, {vdate}")
    append_log_messageV1(main_app, "-----------------------------------------")


    if istatus != 0:
        handle_tpindx_error(main_app, istatus, init_file)
        append_log_messageV2(main_app, log_buffer)
        return
    else:
        log_buffer.write(dec(logmsg))

    # title = dec(title)
    # heading = dec(heading)
    demfil = dec(demfil)
    dirfil = dec(dirfil)
    suffix = dec(suffix)
    folder = dec(folder)

    # 构造绝对路径
    folder_abs = os.path.join(str(init_dir), folder) if not os.path.isabs(folder) else folder
    if output_folder:
        folder_abs = str(output_folder)
    dem_path = os.path.join(str(init_dir), demfil) if not os.path.isabs(demfil) else demfil
    dir_path = os.path.join(str(init_dir), dirfil) if not os.path.isabs(dirfil) else dirfil

    dem_info = ssizgrd(dem_path)
    row = dem_info['row']
    col = dem_info['col']
    celsiz = dem_info['celsiz']
    nodat_dem = dem_info['nodat']  # DEM 的 NODATA 值（浮点）
    clcnt = dem_info['ctr']  # 有效单元数
    dem_2d = np.asarray(dem_info['data'], dtype=np.float32)
    nodat_dem_f32 = np.float32(nodat_dem)
    valid_mask = (np.abs(dem_2d - nodat_dem_f32) >= np.float32(0.1))
    rc = row * col
    prm = 2 * col
    log_buffer.write(f"Parameters for file--> {demfil}\n")
    log_buffer.write("Data cells, Rows, Columns\n")
    log_buffer.write(f"{clcnt} {row} {col}\n")
    append_log_messageV1(main_app, 'Reading elevation grid data')
    grid_data = srdgrd1(dem_info)
    z = grid_data['pf']
    cel = grid_data['cel']
    """
    jbc:
    Actually, our logic can be simplified further by merging the srdgrd and srdgrd1 functions.
    But here I won't show it. HAHA
    """
    # ---- 高程排序 ----
    if clcnt == 1:
        indx = np.array([1], dtype=np.int32)
        lkup = np.array([1], dtype=np.int32)
    else:
        # 调用官方Fortran sindex，返回1基升序索引
        indx = np.asarray(topoindex.sindex(z), dtype=np.int32)
        # 对应官方：lkup(indx(i)) = i
        lkup = np.empty(clcnt, dtype=np.int32)
        lkup[indx - 1] = np.arange(1, clcnt + 1, dtype=np.int32)
    append_log_messageV1(main_app, 'Initial elevation indexing completed')
    # 检查流向文件是否存在
    ans = os.path.exists(dir_path)
    if ans:
        # 文件存在，记录日志
        log_buffer.write("Reading flow-direction data\n")
        append_log_messageV1(main_app, 'Reading flow-direction data')
        # 读取流向数据
        dir_info = rdflodir(dir_path)
        dir_flat = dir_info['dir']
        dir_nodat = dir_info['nodat']
        # dir_geotransform = dir_info['geotransform']
        # dir_projection = dir_info['projection']
        # 错误检查：流向值是否合法（与原 Fortran 完全一致）
        max_dir_val = np.max(dir_flat)
        if (int(max_dir_val) > 9 and aif == 2) or (int(max_dir_val) > 255 and aif == 1):
            err_msg = 'Error in direction grid file. Spurious value detected'
            append_log_messageV1(main_app, err_msg)
            append_log_messageV1(main_app, 'Make corrections to direction grid file before proceeding.')
            log_buffer.write(err_msg + '\n')
            append_log_messageV2(main_app, log_buffer)
            return
        # 设置整数型 NODATA
        nodata = int(dir_nodat)
        # 如果需要转换流向格式
        if aif == 1:
            append_log_messageV1(main_app, 'Converting directional data')
            log_buffer.write("Converting directional data from ESRI to TopoIndex\n")
            # 调用 mpfldr
            mpfldr(dir_flat, nodata)
            # 如果 op(5) 为真，输出转换后的流向栅格（GeoTIFF）
            if op[4]:
                outfil = os.path.join(folder_abs, f"{drofil}{suffix}{rext}")
                dir_2d_out = np.asarray(dir_flat, dtype=np.int32).reshape((row, col), order='F')
                yield_(stop_event)
                isvgrd(dir_2d_out[valid_mask], dem_2d, dir_path, outfil, nodat_dem, log_buffer, main_app, nodata)
                log_buffer.write("Converted flow direction grid saved.\n")
    else:
        # 流向文件不存在，处理与 Fortran 中 else 分支相同
        log_buffer.write("\n")
        log_buffer.write(f"Parameters for file--> {demfil}\n")
        log_buffer.write("Data cells, Rows, Columns\n")
        log_buffer.write(f"{clcnt} {row} {col}\n")
        log_buffer.write("\n")
        log_buffer.write("Flow-direction data not available\n")
        append_log_messageV1(main_app, 'Flow-direction data not available')
        # 写网格尺寸参数文件
        outfil = os.path.join(folder_abs, f"{sizfil}.txt")
        with open(outfil, 'w') as f:
            f.write('imax      nrow      ncol      nwf\n')
            dsctr = 1
            f.write(f"{clcnt} {row} {col} {dsctr}\n")
            f.write('\n')
        # 记录日期时间到日志
        current_time = datetime.now()
        log_buffer.write(f"Date: {current_time.strftime('%m/%d/%Y')}\n")
        log_buffer.write(f"Time: {current_time.strftime('%H:%M:%S')}\n")
        append_log_messageV2(main_app, log_buffer)
        return

    # 流向二维数组：将展平的 dir_flat 重塑为 (row, col) 再转置
    dir_2d_rowmajor = dir_flat.reshape((row, col), order='F')  # 因为 dir_flat 是列优先展平，重塑回 (row, col) 需用 order='F'
    # 但 Fortran 中 dir 的第一维是 ncol，第二维是 nrow，所以需要转置
    dir_2d_fortran = np.asfortranarray(dir_2d_rowmajor.T)  # 转置后 shape (ncol, nrow)，并确保 Fortran 连续
    cel_2d_fortran = np.asfortranarray(np.asarray(cel, dtype=np.int32).reshape((row, col), order='C').T)
    # 高程二维数组也需要转置为 (ncol, nrow)，并确保 Fortran 连续
    dem_2d_fortran = np.asfortranarray(dem_2d.T)  # 转置后 shape (ncol, nrow)
    # 输出列表文件路径
    # save_list = bool(op[0])  # op[0] 对应 op(1)

    if bool(op[0]):
        list_file = os.path.join(str(folder_abs), f"{opthfil}_{suffix}.txt")
    else:
        list_file = ""  # 占位，不会实际使用
    # 调用（参数顺序根据 f2py 生成的签名：rc, prm, nodat, nodata, z, dir, cell, save_list, list_file, nrow, ncol）
    append_log_messageV1(main_app, 'Finding D8 neighbor cells（写 TIdsneiList 列表，大网格约 1 分钟，请耐心等待）')
    cels, mmcnt, logmsg_nxt, istatus_nxt = topoindex.nxtcel(
        rc, prm, nodat_dem, nodata, dem_2d_fortran, dir_2d_fortran, cel_2d_fortran,
        bool(op[0]), fortran_path(list_file) if list_file else b"", row, col)

    # 处理日志
    if logmsg_nxt:
        log_buffer.write(dec(logmsg_nxt))

    # 检查结果
    if istatus_nxt != 0:
        append_log_messageV1(main_app, f"nxtcel failed, code: {istatus_nxt}")
        append_log_messageV2(main_app, log_buffer)
        return

    append_log_messageV1(main_app, f'Correcting cell index numbers（itmax={itmax}，约 30 秒，请耐心等待）')
    rndx, ordr, cctr, logmsg_order, istatus_order = \
        topoindex.correct_order(itmax, indx, lkup, cels[:clcnt], clcnt)

    if logmsg_order:
        log_buffer.write(dec(logmsg_order))

    if istatus_order != 0:
        append_log_messageV1(
            main_app,
            f"correct_order 未收敛（itmax={itmax}）：请增大 tpx_in.txt 中的 "
            f"itmax（迭代次数）后重试，否则 ndxfil / dscfil / wffil 等产物不会生成。")
        append_log_messageV2(main_app, log_buffer)
        return

    append_log_messageV1(main_app, 'Computing weighting factors（写 TIdscelList / TIwfactorList，大网格约 2 分钟，请耐心等待）')
    if pwr < 0 and bool(op[5]):  # op(6) 对应索引 5
        append_log_messageV1(main_app, 'Ridge crest locations cannot be computed with D-infinity option')
        log_buffer.write('Ridge crest locations cannot be computed with D-infinity option\n')
    outfil = os.path.join(str(folder_abs), f"{dscfil}{suffix}.txt")
    outfil1 = os.path.join(str(folder_abs), f"{wffil}{suffix}.txt")
    if lspars:
        spars = 6
    else:
        spars = 5
    # 注意：slofac 的签名是
    #   slofac(z, celsiz, nodat, nodata, cel, dscfil, pwr, next, wffil, dir, spars)
    # 其中 next 就是 nxtcel 返回的下游单元数组 cels。这里改用关键字传参，
    # 避免位置参数错位（历史上曾把 pwr 之后的参数传错）。
    dsctr, ridge, logmsg_slofac, istatus_slofac = \
        topoindex.slofac(
            z=dem_2d_fortran,
            celsiz=celsiz,
            nodat=nodat_dem,
            nodata=nodata,
            cel=cel_2d_fortran,
            dscfil=fortran_path(outfil),
            pwr=pwr,
            next=cels,
            wffil=fortran_path(outfil1),
            dir=dir_2d_fortran,
            spars=spars,
        )
    if logmsg_slofac:
        log_buffer.write(dec(logmsg_slofac))
    if istatus_slofac != 0:
        append_log_messageV1(main_app, '*** Error opening output file ***')
        append_log_messageV1(main_app, f"'--> ', {outfil}")
        append_log_messageV1(main_app, 'Check file path and status')
        append_log_messageV2(main_app, log_buffer)
        return
    append_log_messageV1(main_app, 'Saving results to disk')
    # op(2)：保存D8下游邻居单元栅格
    if bool(op[1]):
        outfil = os.path.join(str(folder_abs), f"{celfil}{suffix}{rext}")
        yield_(stop_event)
        isvgrd(cels, dem_2d, dem_path, outfil, nodat_dem, log_buffer, main_app, nodata)
    # op(3)：保存计算顺序栅格
    if bool(op[2]):
        outfil = os.path.join(str(folder_abs), f"{ndxfil}{suffix}{rext}")
        yield_(stop_event)
        isvgrd(ordr, dem_2d, dem_path, outfil, nodat_dem, log_buffer, main_app, nodata)
    # op(4)：保存单元号与索引号列表
    if bool(op[3]):
        outfil = os.path.join(str(folder_abs), f"{ndxlst}{suffix}.txt")
        append_log_messageV1(main_app, 'Writing cell number and index list')
        istatus_list = topoindex.write_index_list(rndx[:clcnt], fortran_path(outfil), clcnt)
        if istatus_list != 0:
            log_buffer.write(f"Unable to create index list: {outfil}\n")
            append_log_messageV1(main_app, 'Unable to create cell number and index list')
            append_log_messageV2(main_app, log_buffer)
            return
        log_buffer.write(f"Cell number and index list saved: {outfil}\n")
        append_log_messageV1(main_app, 'Cell number and index list saved')

    # op(6)：保存山脊栅格
    if pwr >= 0 and bool(op[5]):
        outfil = os.path.join(str(folder_abs), f"{rdgfil}{suffix}{rext}")
        yield_(stop_event)
        isvgrd(ridge, dem_2d, dem_path, outfil, nodat_dem, log_buffer, main_app, nodata)

    # 写出TRIGRS网格尺寸参数
    if dsctr > 1:
        outfil = os.path.join(str(folder_abs), f"{sizfil}.txt")
        append_log_messageV1(main_app, 'Writing grid size parameters')

        with open(outfil, 'w', encoding='utf-8', newline='\n') as file:
            file.write('imax      nrow      ncol      nwf\n')
            file.write(f"{clcnt} {row} {col} {dsctr}\n\n")

        log_buffer.write(f"Parameters for file--> {demfil}\n")
        log_buffer.write(f"Exponent {pwr}\n")
        log_buffer.write("Data cells, Rows, Columns, Downslope cells\n")
        log_buffer.write(f"{clcnt} {row} {col} {dsctr}\n\n")

    current_time = datetime.now()
    log_buffer.write('TopoIndex finished normally\n')
    log_buffer.write(f"Date: {current_time.strftime('%m/%d/%Y')}\n")
    log_buffer.write(f"Time: {current_time.strftime('%H:%M:%S')}\n")
    append_log_messageV1(main_app, 'TopoIndex finished normally')
    append_log_messageV2(main_app, log_buffer, True, folder_abs)


if __name__ == "__main__":
    # 命令行用法：
    #   python -m topoindex.topoindex <tpx_in.txt>
    import sys as _sys

    _argv = _sys.argv[1:]
    if not _argv:
        print("用法: python -m topoindex.topoindex <tpx_in.txt>")
        _sys.exit(0)
    topoindex_main(True, _argv[0])
