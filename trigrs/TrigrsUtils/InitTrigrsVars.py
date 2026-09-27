import math
from datetime import datetime

from ..TrigrsModule.ModelVars import model_vars


def __init_trigrs_vars():
    fminfil = 'TRfs_min_'.strip()
    zfminfil = 'TRz_at_fs_min_'.strip()
    pminfil = 'TRp_at_fs_min_'.strip()
    profil = 'TRlist_z_p_fs_'.strip()
    wtabfil ='TRwater_'
    # 此处对应trigrs源代码的：！first executable statement............
    # 获取当前日期和时间
    date = datetime.now().strftime('%Y%m%d')
    time = datetime.now().strftime('%H%M%S')
    # 初始化
    model_vars.test = -9999.0
    model_vars.test1 = -9999.0
    pid = ['Ti', 'GM', 'TR']
    model_vars.pi = math.pi
    model_vars.dg2rad = model_vars.pi / 180.0
    vrsn = '2.1.00_Python版'
    bldate = '2025年9月11日'
    model_vars.smt = 0.1  # 早期时间的测试值
    model_vars.lard = 12.0
    return fminfil, zfminfil, pminfil, profil, date, time, pid, vrsn, bldate, wtabfil