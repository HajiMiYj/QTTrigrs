def __message_request(message: str, log_file, level: int = None) -> None:
    """
    处理信息接口，统一日志接口，注意，这里是
    __print_trigrs_title(vrsn, bldate)
    log_file = __check_log_file_path(outfil, vrsn, bldate, date, time)
    这两个函数会用到

    :param message: 信息内容
    :param log_file: 日志文件对象
    :return: None
    """
    print(message)
    if log_file:
        log_file.write(message)


class VerboseMessage:
    """
    处理信息接口，统一日志接口
    这里面分为了
    info_message
    warn_message
    error_message
    如果二次开发的时候，可以针对不同的层给不同的输出
    调用实例
    # 首次调用
    verbose_message = VerboseMessage(log_file)
    # 二次调用
    verbose_message.message_request(info_message = "这是信息")
    每次处理完信息以后就应该重新传入信息
    """

    def __init__(self, log = None):
        self.log = log
        self.info_message = None
        self.warn_message = None
        self.error_message = None
        # 这个log应该在主函数里给一个文件IO对象

    def log_write(self, message: str):
        if self.log:
            self.log.write(message)

    def message_request(self, info_message: str = None, warn_message: str = None, error_message: str = None):
        self.info_message = info_message
        self.warn_message = warn_message
        self.error_message = error_message

        # 这里后续可以设置不同的报错信息可以给不同的逻辑
        if self.info_message:
            print(self.info_message)
            self.log_write(self.info_message)
        elif self.warn_message:
            print(self.warn_message)
            self.log_write(self.warn_message)
        elif self.error_message:
            print(self.error_message)
            self.log_write(self.error_message)
        else:
            self.log.close()
            raise ValueError("检查是否传入了信息")
        # 每次处理完信息后，清空信息
        self.info_message = self.warn_message = self.error_message = None
