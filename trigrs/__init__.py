"""
TRIGRS v2.1 计算内核（从 DizaiGIS4 抽取的独立实现）。

力学求解（steady / rnoff / savage / iverson / satinf / satfin / unsinf /
unsfin 及其辅助过程）由 Fortran(f2py) 内核 ``trigrs.trigrs_f2py`` 完成，
Python 侧只负责 IO（读输入、读栅格、写结果）与列表输出。

与根目录下并列的 ``topoindex`` 包配合使用（先 TopoIndex，后 TRIGRS）。
"""
from __future__ import annotations

__version__ = "2.1.0"
