"""
统一日志输出：控制台日志与缓冲区日志都由上层集中处理。

这里只负责 ``print``——Python 的 print 会被后台上层用
:class:`log_control.LogCapture` 捕获，与 Fortran 的 ``write(*,*)`` 一起
进入同一个缓冲区；运行结束后由上层一次性 flush / 落盘，不再在每个函数
结束时各自处理日志。
"""
from __future__ import annotations


def append_log_messageV1(main_app, message):
    """控制台日志（经 LogCapture 统一进入缓冲区 + 实时回传界面）。"""
    print(str(message))


def append_log_messageV2(main_app, log_buffer, save_flag=False, folder_abs="TopoIndexLog.txt"):
    """把缓冲区内容整段打印出去（由上层统一落盘），不再在此处写文件。"""
    print(log_buffer.getvalue())
