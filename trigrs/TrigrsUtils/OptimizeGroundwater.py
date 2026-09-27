import numpy as np

from ..TrigrsModule.Grids import grids
from ..TrigrsModule.InputVars import input_vars


def optimize_groundwater():
    """
    根据“grids”模块中的最小深度和“zmax”值调整“input_vars”模块中的“zmin”值。
    1从grids.depth数组中计算最小深度（`mndep`）。
    2从grids.zmax数组中计算出最小的 zmax（`mnzmx`）。
    3将input_vars.zmin与mnzmx和mndep进行比较。
    如果input_vars.zmin大于这两个值中的任何一个，就将input_vars.zmin重置为 0。
    """
    mndep = np.min(grids.depth)
    mnzmx = np.min(grids.zmax)
    if input_vars.zmin > mnzmx or input_vars.zmin > mndep:
        input_vars.zmin = 0
