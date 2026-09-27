import numpy as np


class InputVars:
    def __init__(self):
        """
        1. 逻辑变量（logical）
        ans
        一般用作流程判断的临时变量，表示“答案/是否成功”等。
        outp(8)
        输出开关数组，控制各类输出文件是否生成（如安全系数、入渗率、径流等）。
        rodoc
        是否输出径流栅格文件。
        lskip
        是否跳过某些计算或步骤。
        lany
        一般用于判断是否有“任何”条件成立。
        llus
        土地利用相关开关。
        lps0
        饱和度初值相关开关。
        unsat0
        是否采用非饱和模型（控制是否进行非饱和带水分运移计算）。
        bkgrof
        是否考虑背景径流（background runoff）。
        lasc
        是否输出 ASCII 栅格文件。
        lpge0
        是否允许负压力头等相关逻辑。
        igcapf
        是否使用“初始地下水位掩膜”功能。
        unsat(:)
        每个格点是否为非饱和模型（数组）。
        igcap(:)
        每个格点是否有初始地下水位掩膜（数组）。
        2. 整型变量（integer）
        imax
        有效格点总数（整个模拟域的主单元数）。
        row, col
        栅格的行数和列数。
        nwf
        稀疏邻接表的边数（用于径流路由）。
        tx
        每期的时间步数（或时间步调整因子）。
        nmax
        最大单元数（通常与 imax 相关）。
        flag
        控制模型分支、输出类型等的主开关（如 -1、-2、-3、-4 等）。
        nper
        降雨期数（或模拟期数）。
        spcg
        空间分组编号或相关控制参数。
        nzs
        土层数（z方向分层数）。
        mmax
        最大材料类型编号。
        nzon
        区域（zone）数量。
        nout
        输出时刻数（或输出文件数）。
        ksav(:)
        输出时刻对应的时间步编号（指针数组）。
        uijz(:)
        用于输出文件编号或索引的辅助数组。
        3. 浮点型变量（real）
        uww
        未饱和带相关参数（如水头、含水量等）。
        zmin
        最小高程（DEM）。
        t
        当前模拟时刻或总模拟时长。
        dep
        深度相关参数（如初始水位深度）。
        czmax
        最大土层厚度或相关参数。
        crizero
        初始降雨强度。
        slomin, slomax
        坡度最小值和最大值。
        deepz
        深层地下水位或相关深度。
        ths(:)
        各土层的饱和含水量。
        thr(:)
        各土层的残余含水量。
        alp(:)
        各土层的 van Genuchten α 参数（非饱和模型用）。
        dif(:)
        各土层的水分扩散系数。
        c(:)
        各土层的相关参数（如比热、渗透系数等）。
        phi(:)
        各土层的孔隙度或相关物理量。
        ks(:)
        各土层的饱和渗透系数（关键水文参数）。
        de
        深层相关参数（如深层厚度）。
        uws(:)
        各格点的未饱和带初始水头或相关参数。
        capt(:)
        各降雨期的起止时刻（或累计时刻）。
        cri(:)
        各降雨期的降雨强度（可为常数或数组）。
        tsav(:)
        各输出时刻（保存结果的时间点）。
        4. 字符型变量（character）
        flowdir
        流向编码（如 "EAST", "WEST", "D8" 等）。
        el_or_dep
        标记高程或深度的变量类型（如 "elev" 或 "dep"）。
        deepwat
        深层地下水相关标记（如 "deep"）。
        """

        # 逻辑变量
        self.ans = False
        self.outp = np.zeros(8, dtype=bool)
        self.rodoc = False
        self.lskip = False
        self.lany = False
        self.llus = False
        self.lps0 = False
        self.unsat0 = False
        self.bkgrof = False
        self.lasc = False
        self.lpge0 = False
        self.igcapf = False

        # 整型变量
        self.imax = 0
        self.row = 0
        self.col = 0
        self.nwf = 0
        self.tx = 0
        self.nmax = 0
        self.flag = 0
        self.nper = 0
        self.spcg = 0
        self.nzs = 0
        self.mmax = 0
        self.nzon = 0
        self.nout = 0
        # 动态整型数组
        # 动态逻辑数组
        self.unsat = np.array([], dtype=bool)
        self.igcap = np.array([], dtype=bool)
        self.ksav = np.array([], dtype=np.int32())
        self.uijz = np.array([], dtype=np.int32())
        # 实型变量
        self.uww = 0.0
        self.zmin = 0.0
        self.t = 0.0
        self.dep = 0.0
        self.czmax = 0.0
        self.crizero = 0.0
        self.slomin = 0.0
        self.slomax = 0.0
        self.deepz = 0.0
        # 动态实型数组
        self.ths = np.zeros([], dtype=np.float64())
        self.thr = np.zeros([], dtype=np.float64())
        self.alp = np.zeros([], dtype=np.float64())
        self.dif = np.zeros([], dtype=np.float64())
        self.c = np.zeros([], dtype=np.float64())
        self.phi = np.zeros([], dtype=np.float64())
        self.ks = np.zeros([], dtype=np.float64())
        self.uws = np.zeros([], dtype=np.float64())
        self.capt = np.zeros([], dtype=np.float64())
        self.cri = np.zeros([], dtype=np.float64())
        self.tsav = np.zeros([], dtype=np.float64())
        # 字符串变量
        self.flowdir = ''
        self.el_or_dep = ''
        self.deepwat = ''

    def print_self(self):
        print(self.__dict__)


input_vars = InputVars()
