"""
QTTrigrs —— TRIGRS / TopoIndex 独立桌面程序入口。

从 DizaiGIS4 中抽取出来的小项目：不带任何 QGIS 依赖，栅格一律从磁盘文件
选择（RasterPathEdit），TRIGRS 力学计算由 Fortran(f2py) 内核完成。

用法::

    python main.py

界面分三页：
  1. TRIGRS 模型      —— 官方 tr_in.txt 的全部参数
  2. TopoIndex 地形指数 —— 官方 tpx_in.txt 的全部参数
  3. 输入文件预览      —— 实时显示将写出的 tr_in.txt / tpx_in.txt
"""
from __future__ import annotations

import sys


def main() -> int:
    from PyQt5.QtWidgets import QApplication

    from ui.trigrs_controller import TrigrsPanel

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    panel = TrigrsPanel()
    panel.resize(1180, 860)
    panel.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
