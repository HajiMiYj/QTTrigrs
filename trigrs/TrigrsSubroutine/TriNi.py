# import sys
from io import TextIOWrapper
import numpy as np

from ..TrigrsIO.CheckInitFile import __check_init_file_path, __trini_except_420, \
    __trini_except_421, __trini_except_422, __trini_except_424, __trini_except_423
from ..TrigrsModule.Grids import grids
from ..TrigrsModule.InputFileDefs import input_file_defs
from ..TrigrsModule.InputVars import input_vars
from ..TrigrsModule.ModelVars import model_vars
from ..TrigrsUtils.MessageRequest import VerboseMessage


# -----------------------------------------读取子逻辑↓
def __read_value_from_lines(line: str, number: int) -> list:
    """
    读取列数据的值，列数据允许在行后有# xxx的注释
    :param line:传入某一行
    :param number:传入这一行你需要多少个参数
    :return:一个列表
    """
    line = line.split('#')[0].strip()
    # 用逗号或空格分隔
    line_strip = [value.strip() for value in line.replace(',', ' ').split() if value.strip()]
    values = [value for value in line_strip]
    while len(values) < number:
        values.append("")
    return values[:number]


def __read_heading(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int) -> int:
    """
    读取输入文件的列名,任务就是读一行，写一行，行号加1，返回行号
    :param tr_in_file:输入文件
    :param verbose_message:消息处理实例
    :param linct:行号
    :return: 行号
    """
    input_file_defs.heading = tr_in_file.readline().strip()
    info_message = input_file_defs.heading
    verbose_message.message_request(info_message=info_message)
    linct += 1
    return linct


def __read_project_information(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int) -> int:
    """
    1.读取Name of project
    不可复用，故不注释
    """
    linct = __read_heading(tr_in_file, verbose_message, linct)
    input_file_defs.title = tr_in_file.readline().strip()
    linct += 1
    info_message = input_file_defs.title + '\n'
    verbose_message.message_request(info_message=info_message)
    return linct


def __read_tx_nmax_mmax_zones(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int) -> int:
    """
    2.读取tx,nmax,mmax,zones
    不可复用，故不注释
    """
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    linct += 1
    tx, nmax, mmax, nzon = __read_value_from_lines(line, 4)
    info_message = (f"{tx}, "
                    f"{nmax}, "
                    f"{mmax}, "
                    f"{nzon} \n")
    verbose_message.message_request(info_message=info_message)
    input_vars.tx = int(tx)
    input_vars.nmax = max(2, int(nmax))
    input_vars.mmax = int(mmax)
    input_vars.nzon = int(nzon)
    return linct


def __read_nzs_zmin_uww_nper_t(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int) -> int:
    """
    3.读取nzs，zmin，uww，nper，t
    不可复用，故不注释
    """
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    linct += 1
    nzs, zmin, uww, nper, t = __read_value_from_lines(line, 5)
    info_message = (f"{nzs}, "
                    f"{zmin}, "
                    f"{uww}, "
                    f"{nper}, "
                    f"{t}\n")
    verbose_message.message_request(info_message=info_message)
    input_vars.nzs = int(nzs)
    input_vars.zmin = float(zmin)
    input_vars.uww = float(uww)
    input_vars.nper = int(nper)
    input_vars.t = float(t)
    return linct


def __read_czmax_dep_crizero_slomin_slomax(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int,
                                           dg2rad) -> int:
    """
    4.读取zmax,   depth,   rizero,  Min_Slope_Angle (degrees), Max_Slope_Angle (degrees)
    """
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    czmax, dep, crizero, slomin, slomax = __read_value_from_lines(line, 5)
    info_message = (f"{czmax}, "
                    f"{dep}, "
                    f"{crizero}, "
                    f"{slomin}, "
                    f"{slomax}\n")
    linct += 1
    verbose_message.message_request(info_message=info_message)
    input_vars.czmax = float(czmax)
    input_vars.dep = float(dep)
    input_vars.crizero = float(crizero)
    input_vars.slomin = 0.0 if float(slomin) < 0.0 or float(slomin) >= float(slomax) else float(slomin)
    input_vars.slomax = 90.0 if float(slomax) < 0.0 or float(slomax) > 90.0 else float(slomax)
    input_vars.slomax = input_vars.slomax * dg2rad
    input_vars.slomin = input_vars.slomin * dg2rad
    return linct


def __init_parameters_not_mentioned() -> None:
    """
    5.初始化其他未曾提及的参数
    (c(nzon),phi(nzon),uws(nzon),dif(nzon),ks(nzon),ths(nzon),thr(nzon),alp(nzon),unsat(nzon))
    unsat0,igcapf
    """
    nzon = input_vars.nzon
    input_vars.c = np.zeros(nzon)
    input_vars.phi = np.zeros(nzon)
    input_vars.uws = np.zeros(nzon)
    input_vars.dif = np.zeros(nzon)
    input_vars.ks = np.zeros(nzon)
    input_vars.ths = np.zeros(nzon)
    input_vars.thr = np.zeros(nzon)
    input_vars.alp = np.zeros(nzon)
    input_vars.unsat = np.ones(nzon, dtype=bool)  # 全部为 True
    input_vars.unsat0 = False  # 单个布尔变量
    input_vars.igcap = np.zeros(nzon, dtype=bool)  # 全部为 False
    input_vars.igcapf = True  # 单个布尔变量


def __read_soil_layer(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int, dg2rad) -> int:
    """
    6.获取土层参数
    """
    for i in range(input_vars.nzon):
        # 读：Zone[i]
        line = tr_in_file.readline().strip()
        linct += 1
        scratch, value = __read_value_from_lines(line, 2)
        info_message = f'{scratch}：{value}\n'
        verbose_message.message_request(info_message=info_message)
        # 读第i层土层的列名
        input_file_defs.heading = tr_in_file.readline().strip()
        info_message = f'{input_file_defs.heading}\n'
        verbose_message.message_request(info_message=info_message)
        linct += 1
        # 读第i层土层的值
        line = tr_in_file.readline().strip()
        linct += 1
        c_i, phi_i, uws_i, dif_i, ks_i, ths_i, thr_i, alp_i = __read_value_from_lines(line, 8)
        input_vars.c[i] = float(c_i)
        input_vars.phi[i] = float(phi_i)
        input_vars.uws[i] = float(uws_i)
        input_vars.dif[i] = float(dif_i)
        input_vars.ks[i] = float(ks_i)
        input_vars.ths[i] = float(ths_i)
        input_vars.thr[i] = float(thr_i)
        input_vars.alp[i] = float(alp_i)
        # 写入log
        info_message = (f'{c_i}, '
                        f'{phi_i}, '
                        f'{uws_i}, '
                        f'{dif_i}, '
                        f'{ks_i}, '
                        f'{ths_i}, '
                        f'{thr_i}, '
                        f'{alp_i} \n')
        verbose_message.message_request(info_message=info_message)
        # 检查负值
        if any(x < 0 for x in [input_vars.c[i], input_vars.phi[i], input_vars.uws[i], input_vars.dif[i],
                               input_vars.ks[i], input_vars.ths[i], input_vars.thr[i]]):
            error_message = (f"错误，第{linct}行中负属性值\n"
                             f"请编辑 tr_in.txt 文件并重新启动 TRIGRS 程序\n")
            verbose_message.message_request(error_message=error_message)
            tr_in_file.close()
            raise ValueError("错误：401")

        if input_vars.ths[i] > 0.95:
            # 原实现引用了不存在的 input_vars.iz，一旦触发该分支就会抛
            # AttributeError。按上游 TRIGRS 的意图，这里约束的是 θ-sat
            # (ths)，因此改为读写 input_vars.ths[i]。
            warn_message = (f"错误，θ-sat不应大于0.95，{input_vars.ths[i]}\n"
                            f"对于该区域内的单元格，将采用0.45的θ-sat值")
            verbose_message.message_request(warn_message=warn_message)
            input_vars.ths[i] = 0.45

        if input_vars.ths[i] < input_vars.thr[i]:
            input_vars.unsat[i] = False
            warn_message = (f"错误，区域的θ-resid大于θ-sat。\n"
                            f"{input_vars.ths[i]}<{input_vars.thr[i]}\n"
                            f"饱和入渗模型将用于该区域内的单元格\n")
            verbose_message.message_request(warn_message=warn_message)

        if input_vars.alp[i] <= 0:
            input_vars.unsat[i] = False
            warn_message = (f"区域的阿尔法值为负或零{input_vars.alp[i]}<=0\n"
                            f"饱和入渗模型将用于该区域内的单元格")
            verbose_message.message_request(warn_message=warn_message)

        if input_vars.unsat[i]:
            input_vars.unsat0 = True
            warn_message = f"为该区域的单元选择的非饱和渗流模型{i}."
            verbose_message.message_request(warn_message=warn_message)
    input_vars.phi = input_vars.phi * dg2rad
    input_vars.cri = np.zeros(input_vars.nper)  # 对应 Fortran 的 real 数组
    input_vars.capt = np.zeros(input_vars.nper + 2)  # 比 nper 多2个元素
    input_vars.rifil = [''] * input_vars.nper  # 如果是字符串数组，用列表初始化
    return linct


def __read_cri(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int):
    """
    7.获取cri，tol = 从第一层到第input_vars.nper层，先读列名，然后读接下来的tol行代码
    降雨量列表
    """
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    linct += 1
    value = __read_value_from_lines(line, input_vars.nper)
    input_vars.cri = np.array([float(v) for v in value])
    info_message = ', '.join(str(x) for x in input_vars.cri) + '\n'
    verbose_message.message_request(info_message=info_message)
    return linct


def __check_ltdif(ulog, verbose_message: VerboseMessage, linct: int) -> None:
    """
    检查时间序列，如果后续时间比前序时间更短，这显然不对，也就是说input_vars.capt必须得从小到大排列
    否则报错
    """
    ltdif = False
    for j in range(input_vars.nper):
        tdif = input_vars.capt[j + 1] - input_vars.capt[j]
        if tdif < 0.0:
            ltdif = True
    if ltdif:
        __trini_except_424(ulog, linct, verbose_message)


def __read_capt(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int):
    """
    8.获取capt，即降雨量变动对应的时间列表
    """
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    linct += 1
    value = __read_value_from_lines(line, input_vars.nper + 1)
    input_vars.capt[:input_vars.nper + 1] = np.array([float(v) for v in value])
    # 这里要注意，前1~input_vars.nper+1个值是从float(v) for v in value而来
    # 而后一个值，第input_vars.nper + 2个值是input_vars.t
    info_message = (', '.join(str(x) for x in input_vars.capt[:input_vars.nper + 1]) + '\n')
    verbose_message.message_request(info_message=info_message)
    input_vars.capt[input_vars.nper + 1] = input_vars.t
    return linct


def __read_filepath_by_name(name: str, tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int,
                            class_name: int) -> int:
    """
    根据参数名、类名，将所读取的参数值写进对应的类里
    :param name:参数名称，为字符串
    :param tr_in_file:输入文件
    :param verbose_message:消息处理类实例
    :param linct:行号
    :param class_name:整数，1代表input_vars;2代表input_file_defs
    :return:行号
    """
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    linct += 1
    value = __read_value_from_lines(line, 1)
    class_type = None
    if class_name == 1:
        class_type = input_vars
    elif class_name == 2:
        class_type = input_file_defs

    setattr(class_type, name, value[0])
    info_message = f"{getattr(class_type, name)}\n"
    verbose_message.message_request(info_message=info_message)
    return linct


def __read_rifill(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int) -> int:
    linct = __read_heading(tr_in_file, verbose_message, linct)
    input_file_defs.rifil = [""] * input_vars.nper

    for i in range(input_vars.nper):
        line = tr_in_file.readline().strip()
        linct += 1
        input_file_defs.rifil[i] = line
        info_message = f"{line}\n"
        verbose_message.message_request(info_message=info_message)
    return linct


def __transfer_bool(string: str) -> bool | None:
    """
    将读取的T或者.true.转化成布尔值：True
    将读取的F或者.false.转化成布尔值：False
    """
    string = string.strip().lower()
    if string in ['t', 'true', '.true.']:
        return True
    elif string in ['f', 'false', '.false.']:
        return False
    return None


def __read_bool_by_name(name: str, tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int):
    """
    将布尔值写进对应参数名中
    """
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    linct += 1
    value = __transfer_bool(line)
    setattr(input_vars, name, value)
    info_message = f"{line}\n"
    verbose_message.message_request(info_message=info_message)
    return linct


def __read_bool_by_name_index(name: str, index: int, tr_in_file: TextIOWrapper, verbose_message: VerboseMessage,
                              linct: int):
    """
    将布尔值写进对应参数数组中，区别于__read_bool_by_name，前面的name写的是参数名，这个写的是参数数组，还要提供index
    """
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    linct += 1
    value = __transfer_bool(line)
    arr = getattr(input_vars, name)
    arr[index] = value
    info_message = f"{line}\n"
    verbose_message.message_request(info_message=info_message)
    return linct


def __read_water_depth_elevation(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int):
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    linct += 1
    outp_temp, el_or_dep = __read_value_from_lines(line, 2)
    input_vars.outp[0] = __transfer_bool(outp_temp)
    input_vars.el_or_dep = el_or_dep
    info_message = f"{line}\n"
    verbose_message.message_request(info_message=info_message)
    return linct


def __read_flag_spcg(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int) -> int:
    """
    16. 读取flag,spcg
    不可复用，故不注释
    """
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    linct += 1
    flag, spcg = __read_value_from_lines(line, 2)
    info_message = (f"{flag}, "
                    f"{spcg}\n")
    verbose_message.message_request(info_message=info_message)
    input_vars.flag = int(flag)
    input_vars.spcg = float(spcg)
    return linct


def __read_nout(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int) -> int:
    """
    17. 读取nout
    不可复用，故不注释
    """
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    linct += 1
    nout = int(__read_value_from_lines(line, 1)[0])
    if nout < 1:
        nout = 1
    input_vars.nout = nout
    info_message = f"{str(input_vars.nout)}\n"
    verbose_message.message_request(info_message=info_message)
    input_vars.tsav = np.zeros(input_vars.nout)  # 分配并初始化为0
    input_vars.ksav = np.zeros(input_vars.nout)  # 分配并初始化为0
    input_vars.uijz = np.zeros(input_vars.nout)
    return linct


def __read_tsav(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int) -> int:
    """
    17. 读取tsav
    """
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    value = __read_value_from_lines(line, input_vars.nout)
    input_vars.tsav = np.array([float(v) for v in value])
    info_message = (', '.join(str(x) for x in input_vars.tsav) + '\n')
    verbose_message.message_request(info_message=info_message)
    linct += 1
    return linct


def __read_flowdir(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int):
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    linct += 1
    flowdir = __read_value_from_lines(line, 1)[0]
    info_message = f"{flowdir}\n"
    verbose_message.message_request(info_message=info_message)
    input_vars.flowdir = flowdir
    return linct


def __read_deepz_deepwat(tr_in_file: TextIOWrapper, verbose_message: VerboseMessage, linct: int) -> int:
    """
    23.读取deepz,deepwat
    不可复用，故不注释
    """
    linct = __read_heading(tr_in_file, verbose_message, linct)
    line = tr_in_file.readline().strip()
    linct += 1
    deepz, deepwat = __read_value_from_lines(line, 2)
    info_message = (f"{deepz}, "
                    f"{deepwat}\n")
    verbose_message.message_request(info_message=info_message)
    input_vars.deepz = float(deepz)
    input_vars.deepwat = deepwat
    return linct


# -----------------------------------------trini核心逻辑↓
def trini(verbose_message: VerboseMessage, uini: str, dg2rad: float) -> None:
    """
    此函数对应于trini.f95
    :param verbose_message:
    :param uini:tri_in文件路径
    :param dg2rad: 常数pi/180.0
    :return: None
    由于是对实例：input_file_defs、input_vars、model_vars
    以及对文件: log_file,tr_in_file的读写操作，故不设置返回值
    """
    # ----------------初始化逻辑--------------------
    linct = 1
    # verbose_message = verbose_message
    verbose_message.message_request(info_message=f"初始化文件 -->{verbose_message.log.name}\n")
    verbose_message.message_request(info_message="-- 初始化文件列表 --\n")
    tr_in_file = __check_init_file_path(uini, verbose_message)
    # print(f"uini{uini}")
    # ----------------读取逻辑--------------------
    try:
        # 1.读取工程名称
        linct = __read_project_information(tr_in_file, verbose_message, linct)
        # 2.读取tx, nmax, mmax, zones
        linct = __read_tx_nmax_mmax_zones(tr_in_file, verbose_message, linct)
        # 3.读取nzs, zmin, uww, nper, t
        linct = __read_nzs_zmin_uww_nper_t(tr_in_file, verbose_message, linct)
        # 4.读取zmax,   depth,   rizero,  Min_Slope_Angle (degrees), Max_Slope_Angle (degrees)
        linct = __read_czmax_dep_crizero_slomin_slomax(tr_in_file, verbose_message, linct, dg2rad)
        # 5.初始化其他未提及的参数
        __init_parameters_not_mentioned()
        # 6.获取土层参数
        linct = __read_soil_layer(tr_in_file, verbose_message, linct, dg2rad)
        # 7.获取cri[i]
        linct = __read_cri(tr_in_file, verbose_message, linct)
        # 8.获取capt[i]
        linct = __read_capt(tr_in_file, verbose_message, linct)
        # 检查时间序列，小功能
        __check_ltdif(verbose_message, verbose_message, linct)
        # 9.读取slofil、elevfil、zonfil、zfil、depfil、rizerofil
        linct = __read_filepath_by_name("slofil", tr_in_file, verbose_message, linct, 2)
        linct = __read_filepath_by_name("elevfil", tr_in_file, verbose_message, linct, 2)
        linct = __read_filepath_by_name("zonfil", tr_in_file, verbose_message, linct, 2)
        linct = __read_filepath_by_name("zfil", tr_in_file, verbose_message, linct, 2)
        linct = __read_filepath_by_name("depfil", tr_in_file, verbose_message, linct, 2)
        linct = __read_filepath_by_name("rizerofil", tr_in_file, verbose_message, linct, 2)
    except Exception as e:
        # 跳转到处理逻辑
        __trini_except_420(str(e), uini, linct, verbose_message)
    try:
        # 10.读取rifill[i]
        linct = __read_rifill(tr_in_file, verbose_message, linct)
        # 11.读取nxtfil、ndxfil、dscfil、wffil、folder、suffix
        linct = __read_filepath_by_name("nxtfil", tr_in_file, verbose_message, linct, 2)
        linct = __read_filepath_by_name("ndxfil", tr_in_file, verbose_message, linct, 2)
        linct = __read_filepath_by_name("dscfil", tr_in_file, verbose_message, linct, 2)
        linct = __read_filepath_by_name("wffil", tr_in_file, verbose_message, linct, 2)
        linct = __read_filepath_by_name("folder", tr_in_file, verbose_message, linct, 2)
        linct = __read_filepath_by_name("suffix", tr_in_file, verbose_message, linct, 2)
        # 12.读取rodoc，outp(3)，outp(4)，outp(5)，注意out(i)中，index = i - 1
        linct = __read_bool_by_name("rodoc", tr_in_file, verbose_message, linct)
        linct = __read_bool_by_name_index("outp", 2, tr_in_file, verbose_message, linct)
        linct = __read_bool_by_name_index("outp", 3, tr_in_file, verbose_message, linct)
        linct = __read_bool_by_name_index("outp", 4, tr_in_file, verbose_message, linct)
    except Exception as e:
        # 跳转到处理逻辑
        __trini_except_421(str(e), uini, linct, verbose_message)
    try:
        # 14.读取是否保存水头：outp(1)和高程栅格
        linct = __read_water_depth_elevation(tr_in_file, verbose_message, linct)
        # 15.读取outp(6)，outp(7)
        linct = __read_bool_by_name_index("outp", 5, tr_in_file, verbose_message, linct)
    except Exception as e:
        __trini_except_422(str(e), uini, linct, verbose_message)
    try:
        linct = __read_bool_by_name_index("outp", 6, tr_in_file, verbose_message, linct)
    except Exception as e:
        __trini_except_420(str(e), uini, linct, verbose_message)
    try:
        # 16. 读取flag,spcg
        linct = __read_flag_spcg(tr_in_file, verbose_message, linct)
    except Exception as e:
        __trini_except_423(str(e), uini, linct, verbose_message)
    try:
        # 17. 读取nout
        linct = __read_nout(tr_in_file, verbose_message, linct)
        # 18. 读取tsav
        linct = __read_tsav(tr_in_file, verbose_message, linct)
        # 19. 读取lskip，lany，llus，lps0
        linct = __read_bool_by_name("lskip", tr_in_file, verbose_message, linct)
        linct = __read_bool_by_name("lany", tr_in_file, verbose_message, linct)
        linct = __read_bool_by_name("llus", tr_in_file, verbose_message, linct)
        linct = __read_bool_by_name("lps0", tr_in_file, verbose_message, linct)
        # 20. 读取outp(8)
        linct = __read_bool_by_name_index("outp", 7, tr_in_file, verbose_message, linct)
        # 21. 读取flowdir
        linct = __read_flowdir(tr_in_file, verbose_message, linct)
        # 22. 读取bkgrof，lasc，lpge0，igcapf
        linct = __read_bool_by_name("bkgrof", tr_in_file, verbose_message, linct)
        linct = __read_bool_by_name("lasc", tr_in_file, verbose_message, linct)
        linct = __read_bool_by_name("lpge0", tr_in_file, verbose_message, linct)
        linct = __read_bool_by_name("igcapf", tr_in_file, verbose_message, linct)
        # 23. 读取deepz，deepwat
        linct = __read_deepz_deepwat(tr_in_file, verbose_message, linct)
        # 24. 关闭输入文件
        tr_in_file.close()
    except Exception as e:
        __trini_except_423(str(e), uini, linct, verbose_message)
    # ----------------关闭后逻辑-----------------------

    info_message = (f"-- 初始化数据结束 --\n"
                    f"{input_file_defs.title}\n")
    verbose_message.message_request(info_message=info_message)
    for iz in range(input_vars.nzon):
        if input_vars.alp[iz] >= 0 and input_vars.unsat[iz]:
            if input_vars.igcapf:
                # 即使对于较大的毛细水上升带，也使用非饱和模型
                input_vars.igcap[iz] = True
            # 在区间大部分时间都很短的情况下使用饱和模型
            tstar = input_vars.t * input_vars.ks[iz] * input_vars.alp[iz] / (input_vars.ths[iz] - input_vars.thr[iz])
            if tstar < 4.0 * model_vars.smt:
                input_vars.igcap[iz] = False
        if input_vars.igcap[iz]:
            info_message = (f"*********** 区域 {iz + 1} **************\n"
                            f"************采用非饱和渗流模型*************\n")
            verbose_message.message_request(info_message=info_message)
        elif input_vars.igcapf:
            info_message = (f"*********** 区域 {iz + 1} **************\n"
                            f"利用饱和入渗模型避免非饱和入渗模型早期时间的误差\n")
            verbose_message.message_request(info_message=info_message)
        elif input_vars.alp[iz] <= 0:
            info_message = (f"*********** 区域 {iz + 1} **************\n"
                            f"采用饱和入渗模型；α<0.\n")
            verbose_message.message_request(info_message=info_message)
        else:
            info_message = (f"*********** 区域 {iz + 1} **************\n"
                            f"采用非饱和渗流模型，地下水位单元格比{input_vars.alp[iz]}更浅\n"
                            f"视为饱水张力——采用饱水渗透模型。")
            verbose_message.message_request(info_message=info_message)
    info_message = '********  ********  ********  *********\n'
    verbose_message.message_request(info_message=info_message)

    # 输出栅格的扩展名。官方 tr_in.txt 的说明是：
    #   "Specify file extension for output grids.
    #    Enter T (.true.) for \".asc\" or F for \".txt\""
    # 也就是说 lasc = T 对应 .asc、F 对应 .txt。但本实现只支持两种真正的栅格
    # 格式（AAIGrid 和 GeoTIFF）——Ssvgrd 只认 .asc/.tif 两个驱动，写 .txt 会
    # 得到“没有驱动的纯 ASCII 网格”，既不是合法栅格也无法被 GIS 正常打开。
    # 因此这里把语义明确为：lasc = T -> .asc，lasc = F -> .tif，
    # 保证输出的永远是 asc 或 tif，绝不会是 .txt。
    if input_vars.lasc:
        grids.grxt = '.asc'
    else:
        grids.grxt = '.tif'
    pass
