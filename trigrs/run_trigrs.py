"""
TRIGRS 引擎命令行入口。

界面以子进程方式调用本模块，好处有两点：

1. 引擎使用了大量模块级单例（``input_vars`` / ``grids`` / ``model_vars``），
   在同一个 Python 进程里反复运行并不可靠；独立进程可以保证每次运行都是
   干净的状态。
2. 引擎大量使用 ``print`` 输出进度，作为子进程可以实时把日志回传到界面，
   并且用户点“停止”时可以直接结束进程。

用法::

    python -m trigrs.run_trigrs <tr_in.txt> [日志路径]

退出码：
    0   计算完成
    1   参数校验失败（此时不会启动计算）
    2   计算过程中出现异常
"""
from __future__ import annotations

import os
import sys
import traceback


def _usage() -> str:
    return "用法: python -m trigrs.run_trigrs <tr_in.txt> [日志路径]"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help"}:
        print(_usage())
        return 0

    tr_in = argv[0]
    log_path = argv[1] if len(argv) > 1 else "TrigrsLog.txt"

    if not os.path.exists(tr_in):
        print(f"错误：找不到初始化文件 {tr_in}")
        return 1

    # 计算过程中会产生大量 print，这里保持行缓冲，保证界面能实时看到进度。
    try:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass

    try:
        import rasterio  # noqa: F401 - 仅用于给出友好提示
    except Exception as exc:  # pragma: no cover - 仅用于给出友好提示
        print(f"错误：无法加载 rasterio（{exc}）。请安装 rasterio。")
        return 2

    try:
        from .Trigrs import trigrs

        trigrs(tr_in, log_path)
    except SystemExit as exc:  # 引擎内部可能主动退出
        return int(exc.code or 0)
    except Exception as exc:
        print(f"程序执行出现错误: {exc}")
        traceback.print_exc()
        return 2

    print("TRIGRS 计算结束")
    return 0


if __name__ == "__main__":
    sys.exit(main())
