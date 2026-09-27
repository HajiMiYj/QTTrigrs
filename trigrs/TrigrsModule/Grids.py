import numpy as np


class Grids:
    def __init__(self):
        """
        1. 拓扑与索引相关
        pf2(:)
        有效像元线性序列（如模板掩膜），常用于栅格数据的有效单元索引或掩膜。
        indx(:)
        计算顺序索引。Fortran 1基，Python 需转0基。决定每个格点的处理顺序（通常为拓扑排序，保证下游先于上游处理）。
        nxt(:)
        每个格点的下游单元格编号（流向指针），用于径流路由。nxt(i)=i 表示出口单元。
        nv(:), nvu(:)
        备用整型数组，常用于临时计数、标记或辅助索引。
        dsctr(:)
        稀疏邻接表的指针数组，长度 imax+1。dsctr(i):dsctr(i+1)-1 给出格点 i 的所有下游邻接单元在 dsc/wf 中的起止位置。
        dsc(:)
        稀疏邻接表，存储每条“边”对应的下游单元编号。与 dsctr 配合遍历所有下游单元。
        zo(:)
        每个格点的土层号（层索引），用于查找 ks（渗透系数）等分层参数。Fortran 1基，Python 需转0基。
        itemp(:)
        临时整型数组，常用于中间计算或文件读写缓冲。
        2. 水文与物理量相关
        rikzero(:)
        初始归一化入渗率（I/Ks），用于初始条件或边界条件设置。
        rik(:)
        当前归一化入渗率（I/Ks），随时间步更新，形状通常为 imax*nper。
        rik1(:)
        备用归一化入渗率数组，常用于输出或中间结果存储。
        ri(:)
        当前降雨强度（每格），可为常数或栅格输入。
        rizero(:)
        初始降雨强度（每格），用于初始条件。
        pf1(:)
        有效像元线性序列（如模板掩膜），常用于栅格数据的有效单元索引或掩膜。
        temp(:)
        临时浮点数组，常用于文件读写缓冲或中间计算。
        ro(:)
        径流量（每格），随时间步更新。
        wf(:)
        邻接权重（每条边），用于径流分配到下游单元时的比例系数。
        ir(:)
        入渗率（每格），随时间步更新。
        tfg(:)
        临时浮点数组，常用于中间计算。
        zmax(:)
        每格最大高程，常用于地形分析或边界条件。
        slo(:)
        坡度（每格），用于稳定性分析等。
        depth(:)
        地表至水位面的深度（每格），用于水文计算。
        zfmin(:), fsmin(:), pmin(:)
        各格点的最小水位、最小安全系数、最小压力头等，常用于输出或极值分析。
        elev(:)
        每格高程，DEM 数据。
        wtab(:)
        水位面高程（每格），用于输出或分析。
        3. 其它
        grxt
        字符串，存储输出栅格文件的扩展名（如 ".asc"、".tif"），用于文件写出。
        """
        self.pf2 = np.zeros([], dtype=np.int32())
        self.indx = np.zeros([], dtype=np.int32())
        self.nxt = np.zeros([], dtype=np.int32())
        self.nv = np.zeros([], dtype=np.int32())
        self.nvu = np.zeros([], dtype=np.int32())

        self.dsctr = np.zeros([], dtype=np.int32())
        self.dsc = np.zeros([], dtype=np.int32())
        self.zo = np.zeros([], dtype=np.int32())
        self.itemp = np.zeros([], dtype=np.int32())
        self.rikzero = np.zeros([], dtype=np.int32())

        self.rik = np.zeros([], dtype=np.float64())
        self.rik1 = np.zeros([], dtype=np.float64())
        self.ri = np.zeros([], dtype=np.float64())
        self.rizero = np.zeros([], dtype=np.float64())
        self.pf1 = np.zeros([], dtype=np.float64())

        self.temp = np.zeros([], dtype=np.float64())
        self.ro = np.zeros([], dtype=np.float64())
        self.wf = np.zeros([], dtype=np.float64())
        self.ir = np.zeros([], dtype=np.float64())
        self.tfg = np.zeros([], dtype=np.float64())

        self.zmax = np.zeros([], dtype=np.float64())
        self.slo = np.zeros([], dtype=np.float64())
        self.depth = np.zeros([], dtype=np.float64())

        self.zfmin = np.zeros([], dtype=np.float64())
        self.fsmin = np.zeros([], dtype=np.float64())
        self.pmin = np.zeros([], dtype=np.float64())

        self.elev = np.zeros([], dtype=np.float64())
        self.wtab = np.zeros([], dtype=np.float64())

        self.grxt = ''


grids = Grids()
