class InputFileDefs:
    """
    用于存储输入文件相关的全局变量，等价于 Fortran 的 input_file_defs 模块
    1. 字符型变量（character）
    heading
    输入文件的标题或说明信息，通常用于输出文件头部或日志。
    slofil
    坡度栅格文件名（slope file），存储每个格点的坡度信息。
    zonfil
    区域划分文件名（zone file），用于指定不同区域的参数分区。
    zfil
    土层厚度或相关 z 向参数的文件名（z file）。
    depfil
    初始水位深度文件名（depth file），用于指定每个格点的初始地下水深度。
    rizerofil
    初始降雨强度文件名（rizero file），用于指定每个格点的初始降雨强度。
    nxtfil
    下游单元格索引文件名（next file），用于径流路由，每个格点指向其下游格点。
    ndxfil
    计算顺序索引文件名（index file），指定格点的处理顺序（通常为拓扑排序）。
    wffil
    邻接权重文件名（weight file），存储稀疏邻接表中每条边的权重（用于径流分配）。
    dscfil
    稀疏邻接表文件名（descendant file），存储每个格点的下游邻接单元编号。
    init
    初始化文件名（init file），通常为主参数输入文件。
    title
    项目或模拟标题，用于输出或日志。
    elevfil
    高程栅格文件名（elevation file），存储每个格点的高程（DEM）。
    rifil(:)
    降雨强度栅格文件名数组（rainfall intensity file），每个降雨期一个文件。
    folder
    输出文件夹路径，指定所有输出文件的保存目录。
    elfoldr
    输入文件夹路径，指定所有输入文件的读取目录。
    suffix
    文件名后缀，用于区分不同模拟或输出文件（如 "_A"、"_B" 等）。
    """

    def __init__(self):
        self.heading = ""
        self.slofil = ""
        self.zonfil = ""
        self.zfil = ""

        self.depfil = ""

        self.rizerofil = ""
        self.ndxfil = ""
        self.nxtfil = ""

        self.wffil = ""
        self.dscfil = ""
        self.init = ""
        self.title = ""

        self.elevfil = ""

        self.rifil = [""]

        self.folder = ""
        self.elfoldr = ""

        self.suffix = ""


input_file_defs = InputFileDefs()