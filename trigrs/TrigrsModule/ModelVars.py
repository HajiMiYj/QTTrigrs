import numpy as np



class ModelVars:
    """
    这个类对应着trigrs的model_vars.f95
    1. 整型参数
    double
    Fortran 的 kind 常量，指定双精度浮点类型（一般用于 real(double) 声明）。
    nts
    总时间步数（number of time steps），整个模拟的离散步数。
    kper
    有效降雨期数（periods），或当前模拟的期数。
    nmax1, nmax2
    最大单元数相关变量，通常用于数组分配或循环上限。
    nmn, nmin
    最小单元编号或相关下界。
    jsav(:)
    输出时刻对应的时间步编号（指针数组），用于输出控制。
    ix(:), jy(:)
    栅格的行、列索引数组，常用于输出文件或空间定位。
    2. 浮点参数（real/double）
    test1
    测试用浮点变量，常用于调试或临时存储。
    dg2rad
    角度转弧度的系数（一般为 π/180）。
    q(:)
    每个时间步的总流量（surface flux），或其它相关流量。
    qb(:)
    每个时间步的基流（baseflow）或相关流量。
    eps
    极小量，防止除零或数值误差（如 1e-18）。
    tmin, tmax
    最小/最大模拟时刻（起止时间）。
    ts
    当前时间步的时刻。
    qt
    当前时间步的流量。
    tns
    总时间步数（浮点型，便于除法）。
    beta
    斜率相关参数，常用于稳定性分析。
    qmax
    最大流量。
    tinc
    当前时间步长（时间增量）。
    test, nodat, sumex, dusz, dcf, vf0, p0zmx
    其它模型参数：
    test：测试变量
    nodat：无数据值（nodata value）
    sumex：总渗漏量或相关累积量
    dusz, dcf, vf0：模型用的物理或经验参数
    p0zmx：最大初始压力头（added 2013）
    celsiz
    栅格单元边长（cell size）。
    param(6), parami(6)
    模型参数数组及其倒数（如物理常数、经验系数等）。
    ti, tis
    时间步相关参数（如初始时间、最小时间步等）。
    pi
    圆周率 π。
    smt, lard
    平滑参数、相关长度参数。
    xllc, yllc
    栅格左下角坐标（x/y lower left corner）。
    zmn(1), zmx(1)
    DEM 最小/最大高程。
    3. 浮点数组（real/double, allocatable）
    p(:), ptran(:), pzero(:), bline(:), chi(:)
    p(:)：压力头（pressure head）
    ptran(:)：过渡压力头
    pzero(:)：初始压力头
    bline(:)：地下水位线
    chi(:)：稳定性分析相关参数
    r(:)
    每格的径流量或相关变量。
    fc(:), fw(:), thz(:), kz(:), tcap(:), tinc_sat(:)
    fc(:)：田间持水量（field capacity）
    fw(:)：权重或相关参数
    thz(:)：含水量
    kz(:)：分层渗透系数
    tcap(:)：毛细水位
    tinc_sat(:)：饱和模型下的时间步长数组
    trz(:), uwsp(:), gs(:), qtime(:), qts(:)
    trz(:)：分层相关参数
    uwsp(:)：未饱和带压力头
    gs(:)：区域参数
    qtime(:)：每步的时刻
    qts(:)：每步的表面流量
    p3d(:,:), pzero3d(:,:), ptran3d(:,:), fs3d(:,:), th3d(:,:), dh3d(:), newdep3d(:)
    p3d(:,:): 三维压力头（空间×层）
    pzero3d(:,:): 三维初始压力头
    ptran3d(:,:): 三维过渡压力头
    fs3d(:,:): 三维安全系数
    th3d(:,:): 三维含水量
    dh3d(:): 三维压力头变化量
    newdep3d(:): 三维新水位深度
    """
    def __init__(self):
        # 整型变量
        self.nts = 0
        self.kper = 0
        self.nmax1 = 0
        self.nmax2 = 0
        self.nmn = 0
        self.nmin = 0

        # 可变长整型数组（用 numpy int32，初始为空）
        self.jsav = np.array([], dtype=np.int32)
        self.ix = np.array([], dtype=np.int32)
        self.jy = np.array([], dtype=np.int32)

        # 实型变量
        self.test1 = 0.0
        self.dg2rad = 0.0

        # 可变长实型数组（用 numpy float64，初始为空）
        self.q = np.array([], dtype=np.float64)
        self.qb = np.array([], dtype=np.float64)

        # 双精度实型变量
        self.eps = 0.0
        self.tmin = 0.0
        self.tmax = 0.0
        self.ts = 0.0
        self.qt = 0.0
        self.tns = 0.0
        self.beta = 0.0
        self.qmax = 0.0
        self.tinc = 0.0
        self.test = 0.0
        self.nodat = 0.0
        self.sumex = 0.0
        self.dusz = 0.0
        self.dcf = 0.0
        self.vf0 = 0.0
        self.p0zmx = 0.0
        self.celsiz = 0.0
        self.param = np.zeros(6, dtype=np.float64)
        self.parami = np.zeros(6, dtype=np.float64)
        self.ti = 0.0
        self.tis = 0.0
        self.pi = 0.0
        self.smt = 0.0
        self.lard = 0.0
        self.xllc = 0.0
        self.yllc = 0.0
        self.zmn = np.zeros(1, dtype=np.float64)
        self.zmx = np.zeros(1, dtype=np.float64)

        # 可变长双精度数组
        self.p = np.array([], dtype=np.float64)
        self.ptran = np.array([], dtype=np.float64)
        self.pzero = np.array([], dtype=np.float64)
        self.bline = np.array([], dtype=np.float64)
        self.chi = np.array([], dtype=np.float64)
        self.r = np.array([], dtype=np.float64)
        self.fc = np.array([], dtype=np.float64)
        self.fw = np.array([], dtype=np.float64)
        self.thz = np.array([], dtype=np.float64)
        self.kz = np.array([], dtype=np.float64)
        self.tcap = np.array([], dtype=np.float64)
        self.tinc_sat = np.array([], dtype=np.float64)
        self.trz = np.array([], dtype=np.float64)
        self.uwsp = np.array([], dtype=np.float64)
        self.gs = np.array([], dtype=np.float64)
        self.qtime = np.array([], dtype=np.float64)
        self.qts = np.array([], dtype=np.float64)

        # 可变长二维数组（初始为空，后续可用 np.zeros((m, n)) 初始化）
        self.p3d = np.empty((0, 0), dtype=np.float64)
        self.pzero3d = np.empty((0, 0), dtype=np.float64)
        self.ptran3d = np.empty((0, 0), dtype=np.float64)
        self.fs3d = np.empty((0, 0), dtype=np.float64)
        self.th3d = np.empty((0, 0), dtype=np.float64)
        self.dh3d = np.array([], dtype=np.float64)
        self.newdep3d = np.array([], dtype=np.float64)

    def ensure(self, name, shape, dtype=np.float64):
        """
        确保某个数组已按 ``shape`` 分配，没有分配过时才真正分配。

        历史上这些三维结果数组只在 ``flag < 0`` 时按“输出列表”的需求分配，
        但 ``savage`` 等求解子程序无论 flag 取值都会写入它们，导致
        ``flag = 0``（界面默认值）时抛出
        ``IndexError: index 0 is out of bounds for axis 0 with size 0``。
        统一走本方法分配可以避免该类崩溃。

        :param name: 数组属性名，例如 ``"fs3d"``
        :param shape: 需要的形状
        :param dtype: 数据类型
        :return: 分配好的数组
        """
        current = getattr(self, name, None)
        if current is None or current.shape != tuple(shape):
            current = np.zeros(tuple(shape), dtype=dtype)
            setattr(self, name, current)
        return current

# 用法示例
model_vars = ModelVars()
# 后续可根据实际需要分配数组大小，例如：
# model_vars.p3d = np.zeros((imax * nout, nzs + 1), dtype=np.float64)
