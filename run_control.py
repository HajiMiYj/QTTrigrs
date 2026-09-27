"""进程内运行控制：停止请求异常 + 周期让出 GIL 的小工具。

引擎的输出阶段（写栅格、写列表）在后台线程里运行，但 Python 的 GIL 会让
纯 Python 长循环（例如逐单元写列表）抢占解释器，导致界面“未响应”。这里
提供一个统一的 ``StopRequested`` 异常和 ``yield_`` 帮助函数：输出循环每
处理一小段就调用一次，既能让主线程拿到 GIL 刷新界面，也能及时响应停止。
"""
from __future__ import annotations

import threading
import time


class StopRequested(Exception):
    """用户请求停止计算时抛出，用于中断输出/长循环。"""


def yield_(stop_event: threading.Event | None = None, interval: float = 0.0) -> None:
    """让出 GIL，并在需要时检查停止请求。

    :param stop_event: 停止事件（None 表示不可停止）。
    :param interval: 睡眠时长（秒），0 表示仅让出一次。
    """
    if stop_event is not None and stop_event.is_set():
        raise StopRequested()
    if interval:
        time.sleep(interval)
    else:
        time.sleep(0)
