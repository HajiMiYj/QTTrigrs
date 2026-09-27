import os

from ..TrigrsUtils.MessageRequest import __message_request


def __trigrs_except_410(outfil:str,meg_e:str)->None:
    """
    trigrs主程序410的实现
    :param outfil:日志文件路径
    :param meg_e:错误信息
    """
    error_message = (f"{meg_e}\n"
                     f"在TRIGRS主程序中打开输出文件时出错\n"
                     f"--> ,{outfil}\n"
                     f"请检查文件路径和状态\n")
    print(error_message)

def __check_log_file_path(outfil:str, vrsn:str, bldate:str, date:str, time:str):
    """
    检查日志文件是否合法，如果不存在日志路径，直接以410的退出码退出程序
    :param outfil:日志路径
    :param vrsn:版本号
    :param bldate:构建日期
    :param date:日期
    :param time:时间
    """
    try:
        log_dir = os.path.dirname(outfil)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        log_file = open(outfil, 'w')
        info_message = (f"\n"
                        f"开始运行Trigrs：{vrsn} {bldate}\n"
                        f"日期： {date[4:6]}/{date[6:8]}/{date[0:4]}\n"
                        f"时间: {time[0:2]}:{time[2:4]}:{time[4:6]}\n")
        __message_request(info_message,log_file)
        return log_file
    except Exception as e:
        __trigrs_except_410(outfil,str(e))


