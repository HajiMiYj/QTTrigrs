import os
from io import TextIOWrapper

from ..TrigrsModule.InputVars import input_vars
from ..TrigrsModule.InputFileDefs import input_file_defs
from ..TrigrsUtils.MessageRequest import VerboseMessage

# -----------------------------------------报错逻辑↓
"""
注意，这个错误码是模仿tr_in的错误码编写的
"""


def __trini_except_201(e: str, init: str, verbose_message: VerboseMessage):
    error_message = (
        f"210:{e}\n"
        "错误！无法打开初始化文件（tri_ni.py）\n"
        f"文件名：{init}\n"
        "请检查文件位置和名称\n"
    )
    verbose_message.message_request(error_message=error_message)
    raise RuntimeError(error_message)


def __trini_except_420(e: str, init: str, linct: int, verbose_message: VerboseMessage):
    error_message = (
        f"420:{e}\n"
        "错误！读取初始化文件出错（tri_ni.py）\n"
        f"文件名：{init}，出错行号：{linct}\n"
        "请检查文件内容和组织格式\n"
    )
    verbose_message.message_request(error_message=error_message)
    raise RuntimeError(error_message)


def __trini_except_421(e: str, init: str, linct: int, verbose_message: VerboseMessage):
    error_message = (f"421:{e}\n"
                     f"错误！读取初始化文件出错（tri_ni.py）\n"
                     f"文件名：{init}，出错行号：{linct}\n"
                     f"请检查文件内容和组织格式\n"
                     f"降雨数据文件名/占位符数量必须等于{input_vars.nper}，每个文件名单独一行。\n")
    verbose_message.message_request(error_message=error_message)
    raise RuntimeError(error_message)


def __trini_except_422(e: str, init, linct, verbose_message: VerboseMessage):
    error_message = (f"422:{e}"
                     f"错误：读取初始化文件出错（tri_ni.py）\n"
                     f"--> {init}，位于第 {linct} 行\n"
                     f"请检查文件内容和组织格式\n"
                     f"请确保指定了水位或深度，并选择是否保存到文件。\n")
    verbose_message.message_request(error_message=error_message)
    raise RuntimeError(error_message)


def __trini_except_423(e: str, init, linct, verbose_message: VerboseMessage):
    error_message = (f"423:{e}\n"
                     f"错误：读取初始化文件出错（tri_ni.py）\n"
                     f"--> {init}，位于第 {linct} 行\n"
                     f"请检查文件内容和组织格式\n"
                     f"请确保输出标志和垂直间距在同一行指定。\n")
    verbose_message.message_request(error_message=error_message)
    raise RuntimeError(error_message)


def __trini_except_424(init, linct, verbose_message: VerboseMessage):
    error_message = (f"错误：读取初始化文件出错（tri_ni.py）\n"
                     f"--> {init}，位于第 {linct} 行\n"
                     f"请将时间步按递增顺序排列\n"
                     f"请确保输出标志和垂直间距在同一行指定。\n")
    verbose_message.message_request(error_message=error_message)
    raise RuntimeError(error_message)


def __try_open_init_file(init_file: str, verbose_message: VerboseMessage) -> TextIOWrapper:
    """
    打开 tr_in.txt。

    编码必须显式指定：Windows 的默认编码是系统 ANSI（中文系统为 GBK），
    而本模块写出的 tr_in.txt 一律是 UTF-8。工程名之类的字段含中文时，
    用默认编码读会抛
    ``'gbk' codec can't decode byte ...`` 并报成“读取初始化文件出错”，
    看起来像文件格式坏了，其实只是编码不一致。

    这里优先用 UTF-8 打开（兼容官方纯 ASCII 文件），失败再退回系统编码。
    """
    tr_in_file = None
    path = init_file.strip()
    try:
        tr_in_file = open(path, "r", encoding="utf-8", errors="strict")
    except FileNotFoundError as e:
        __trini_except_201(str(e), init_file, verbose_message)
    except UnicodeDecodeError:
        try:
            tr_in_file = open(path, "r", encoding="utf-8", errors="replace")
        except OSError as e:
            __trini_except_201(str(e), init_file, verbose_message)
    except OSError as e:
        __trini_except_201(str(e), init_file, verbose_message)
    if tr_in_file is not None:
        verbose_message.message_request(info_message="正在打开默认初始化文件")
    return tr_in_file


def __check_init_file_path(uini: str, verbose_message: VerboseMessage) -> TextIOWrapper:
    """
    获取初始化文件
    :param uini:tr_in文件路径
    :param verbose_message:消息处理类
    """
    input_file_defs.init = uini
    ans = os.path.exists(input_file_defs.init.strip())
    if ans:
        tr_in_file = __try_open_init_file(input_file_defs.init.strip(), verbose_message)
    else:
        info_message = (f"无法打开初始化文件：{input_file_defs.init}\n"
                        f"输入初始化文件的路径，然后按回车键继续。\n"
                        f"例如：C:\\123.txt")
        verbose_message.message_request(info_message=info_message)
        tr_in_file = __try_open_init_file(input_file_defs.init.strip(), verbose_message)
    return tr_in_file
