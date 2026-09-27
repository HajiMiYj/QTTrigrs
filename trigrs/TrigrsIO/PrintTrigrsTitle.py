from ..TrigrsUtils.MessageRequest import __message_request


def __print_trigrs_title(vrsn:str, bldate:str)->None:
    """
    打印trigrs的title信息
    :param: vrsn:trigrs版本号
    :param: bldate:trigrs构建日期
    :return: None
    """

    info_message = (f"-----------------------------------------\n"
                    f"TRIGRS: 瞬时降雨入渗与基于网格的区域边坡稳定性分析软件\n"
                    f"            版本 {vrsn}, {bldate}\n"
                    f"    By Rex L. Baum and William Z. Savage\n"
                    f"          U.S. Geological Survey\n"
                    f"   python汉化版作者：黄发明，江炳辰，郑天翔\n"
                    f"             南昌大学工程建设学院\n"
                    f"-----------------------------------------\n")
    __message_request(info_message,None)

