# TopoIndex Python 二次开发版

[简体中文](README.md) | [English](README_EN.md) | [第三方与上游声明](THIRD_PARTY_NOTICES.md)

> [!IMPORTANT]
> 本仓库是基于美国地质调查局（USGS）TRIGRS 官方发行版所附 **TopoIndex** 工具进行的非官方二次开发，不是 USGS 官方版本，也不代表 USGS 对本项目的认可、担保或背书。本仓库只实现 TopoIndex 地形预处理流程，不包含完整的 TRIGRS 降雨入渗与边坡稳定性计算程序。

TopoIndex Python 二次开发版通过 GDAL 读取 DEM 与流向栅格，将部分原始 TopoIndex Fortran 计算核心使用 `numpy.f2py` 封装为 Python 扩展，并以 Python 重写部分栅格 I/O、日志和流程控制。它用于生成 TRIGRS 地表径流路由所需的下游单元、流量分配权重、单元索引和网格尺寸等文件。

## 项目定位

本项目能够：

- 读取 GDAL 支持的单波段 DEM 与流向栅格；
- 将 ESRI D8 流向编码转换为 TopoIndex/TRIGRS 编码；
- 按高程建立单元索引并修正计算顺序；
- 识别每个有效单元的 D8 下游单元；
- 使用 D8、均匀分配、坡度幂律或 D-infinity 变体计算径流分配权重；
- 输出带空间参考的 GeoTIFF，以及供 TRIGRS 使用的文本列表和网格尺寸文件；
- 在 Windows 下通过预编译的 CPython 扩展调用 Fortran 核心，也可从源码重新构建。

本项目不能：

- 计算降雨入渗、孔隙水压力或安全系数；
- 独立完成滑坡易发性或危险性评价；
- 替代完整 TRIGRS、官方文档、地质工程判断或专业审查；
- 保证与所有 TRIGRS 版本、所有 GDAL 构建或所有平台二进制兼容。

## 与官方 TRIGRS / TopoIndex 的关系

官方 TRIGRS 是用于模拟浅层降雨诱发滑坡发生时间和空间分布的 Fortran 程序。官方发行版同时包含 TopoIndex、GridMatch 和 UnitConvert 等配套工具。TopoIndex 负责根据 DEM 和流向栅格确定径流路由关系，并为 TRIGRS 准备数组尺寸和权重文件。

本仓库对其中的 TopoIndex 进行了适配：

| 范围 | 本仓库实现 |
| --- | --- |
| 保留并改造的计算逻辑 | `sindex`、`nxtcel`、`slofac`，以及从原主流程拆分/重组的参数读取和索引顺序修正逻辑 |
| Python 重写 | `ssizgrd`、`srdgrd1`、`rdflodir`、`mpfldr`、`isvgrd` 等栅格 I/O 与转换流程 |
| 新增适配层 | `topoindex.py` 流程编排、f2py 接口、类型声明、日志缓冲、构建脚本和 GeoTIFF 输出 |
| 未包含 | 完整 TRIGRS 求解器、GridMatch、UnitConvert、官方示例数据和官方完整文档 |

本地源码保留的上游信息显示原 TopoIndex 作者为 **Rex L. Baum（USGS）**；当前程序横幅中的 `1.0.14 / 11May2015` 是所适配 TopoIndex 代码的内部版本信息，不是本二次开发项目的独立发布版本。

官方入口：

- [TRIGRS v2.1 USGS 软件页面](https://www.usgs.gov/software/trigrs-version-21)
- [USGS 官方代码仓库 v2.1.0](https://code.usgs.gov/usgs/landslides-trigrs/-/tree/v2.1.0)
- [USGS GitHub 历史镜像 v2.1.0](https://github.com/usgs/landslides-trigrs/tree/v2.1.0)
- [TRIGRS 2.0 用户报告](https://doi.org/10.3133/ofr20081159)

## 处理流程

```text
tpx_in.txt
    │
    ├── 解析参数、输入路径和输出开关
    │
DEM ─┼── GDAL 读取、有效单元编号、高程排序
    │
流向 ─┼── GDAL 读取、可选 ESRI D8 编码转换
    │
    ├── Fortran: sindex → nxtcel → correct_order → slofac
    │
    └── GeoTIFF / TRIGRS 文本列表 / 网格尺寸 / 日志
```

## 目录结构

```text
topo_dev/
├── README.md                         # 中文说明
├── README_EN.md                      # English documentation
├── THIRD_PARTY_NOTICES.md            # 上游、依赖、二进制分发声明
├── topoindex.py                      # Python 主流程与公开调用入口
├── build_topoindex.cmd               # Windows f2py 构建脚本
├── build_topoindex.sh                # POSIX 构建脚本（当前加载器仍需适配）
├── src/                              # 改造后的 Fortran 源码
├── topo_rewrite/                     # Python 栅格 I/O 与转换实现
├── topo_utils/                       # 日志与错误处理
├── topoindex_f2py/
│   ├── __init__.py                   # Windows DLL 搜索路径与扩展加载
│   ├── topoindex.pyi                 # f2py 接口类型提示
│   └── topoindex.cp312-win_amd64.pyd # 已提供的 CPython 3.12 / Windows x64 构建
└── lib/                              # 已提供构建所需的 Windows 运行时 DLL
```

`__pycache__/`、`.idea/`、`.pyd` 和 DLL 属于缓存、开发环境或平台相关产物；公开发布前应决定是否保留，并完成相应的二进制许可证核对。

## 运行环境

### 当前已知目标环境

| 组件 | 说明 |
| --- | --- |
| 操作系统 | 当前预编译模块面向 64 位 Windows |
| Python | CPython 3.12；仓库内 `.pyd` 不能由 Python 3.11、3.13 等版本直接加载 |
| NumPy | 开发记录使用 `numpy==1.26.4`；重建时需安装 NumPy 和 f2py |
| GDAL | Python 包必须能够执行 `from osgeo import gdal` |
| 构建工具 | gfortran、Meson、Ninja，以及与目标 Python ABI 兼容的 C/Fortran 工具链 |

推荐在同一个 Conda、OSGeo4W 或其他受控环境中安装并运行 GDAL、NumPy 和 Python，避免混用多个工具链的 DLL。

### Windows 快速安装

如果使用仓库内预编译模块，请准备 **64 位 CPython 3.12**，并在该环境中安装兼容的 NumPy 与 GDAL。GDAL 的 Python 包必须与本机 GDAL 原生库匹配；通常使用 Conda/conda-forge 或 OSGeo4W 比直接混装多个 `pip` 二进制更稳妥。

示例环境仅供参考：

```powershell
conda create -n topoindex-py312 -c conda-forge python=3.12 numpy=1.26.4 gdal
conda activate topoindex-py312
python -c "from osgeo import gdal; import numpy; print(gdal.VersionInfo(), numpy.__version__)"
python -c "from topoindex_f2py import topoindex; print(topoindex.__file__)"
```

如果 `python` 命令实际指向 Microsoft Store 占位程序，请改用环境中真实的 `python.exe`。

## 输入数据要求

### DEM

- GDAL 可读取的单波段栅格；
- 应设置明确的 NODATA 值；未设置时当前实现使用 `-9999.0`；
- 当前算法假设正方形像元，单元尺寸取地理变换中的 X 分辨率绝对值；
- 高程数据在进入 Fortran 核心前转换为 `float32`。

### 流向栅格

- 必须与 DEM 的行列数、像元位置、分辨率、范围及有效/NODATA 掩膜一致；
- 数据转换为 `int32`；
- `aif=1` 表示 ESRI D8 编码，`aif=2` 表示 TopoIndex 编码；
- 当前代码只检查部分数值范围，不能代替完整的栅格一致性检查。

ESRI 与 TopoIndex 编码关系如下：

| 方位 | ESRI D8 | TopoIndex |
| --- | ---: | ---: |
| 西北 | 32 | 1 |
| 北 | 64 | 2 |
| 东北 | 128 | 3 |
| 西 | 16 | 4 |
| 中心/无确定流向 | — | 5 |
| 东 | 1 | 6 |
| 西南 | 8 | 7 |
| 南 | 4 | 8 |
| 东南 | 2 | 9 |

## 初始化文件 `tpx_in.txt`

当前解析器沿用官方 TopoIndex 的固定行序格式：说明行和值行交替出现。不要随意删除、插入或重新排序行。相对路径以 `tpx_in.txt` 所在目录为基准。

```text
TopoIndex Python adaptation; project heading
Example project
Flow-direction numbering scheme (ESRI=1, TopoIndex=2)
1
Exponent, Number of iterations
-1, 10
Name of elevation grid file
data/dem.tif
Name of direction grid
data/directions.tif
Save listing of D8 downslope neighbor cells? T/F
T
Save grid of D8 downslope neighbor cells? T/F
T
Save cell index number grid? T/F
T
Save list of cell number and corresponding index number? T/F
T
Save remapped flow-direction grid? T/F
T
Save ridge-crest grid? T/F; Sparse (T) or dense (F)?
F,T
ID code for output files? (8 characters or less)
demo
```

字段说明：

| 字段 | 含义 |
| --- | --- |
| `aif` | `1`：ESRI D8；`2`：TopoIndex 1–9 编码 |
| `pwr > 20` | 使用最陡下降方向，等价于 D8 路由 |
| `pwr = 0` | 在所有下坡相邻单元之间均匀分配 |
| `pwr = 1` | 按坡度绝对值成比例分配 |
| `0 < pwr <= 20` | 按 `abs(slope) ** pwr` 分配 |
| `pwr < 0` | 使用官方代码中的 D-infinity 变体；仅适用于正方形像元 |
| `itmax` | 修正单元计算顺序的最大迭代次数 |
| 六个 T/F 开关 | 依次控制下游邻居列表、下游邻居栅格、索引栅格、索引列表、重编码流向栅格和山脊栅格 |
| `lspars` | 山脊输出为稀疏 (`T`) 或密集 (`F`)；仅与第六个开关共同使用 |
| `suffix` | 输出文件标识，Fortran 接口最长 8 个字符 |

输出目录由 **DEM 路径中的目录部分**推导。例如 `data/dem.tif` 会把输出写到初始化文件旁的 `data/`。目标目录必须事先存在。

## 运行

推荐从自己的脚本显式调用：

```python
from pathlib import Path

from topoindex import topoindex_main

init_file = Path(r"C:\path\to\project\tpx_in.txt")
topoindex_main(main_app=True, init_file=str(init_file))
```

`main_app=True` 会把进度信息打印到控制台。函数目前不返回结果对象，主要结果写入磁盘。

> [!WARNING]
> `topoindex.py` 文件底部仍保留开发者机器上的示例绝对路径。直接执行 `python topoindex.py` 前必须修改该路径；更推荐使用上面的导入调用方式。不要把个人绝对路径提交到公开发行版。

## 输出文件

假设 `suffix=demo`，当前实现可能生成：

| 文件 | 条件 | 内容 |
| --- | --- | --- |
| `TIdscelList_demo.txt` | 流向文件存在且处理继续 | 每个单元的下游单元列表 |
| `TIwfactorList_demo.txt` | 流向文件存在且处理继续 | 与下游单元对应的径流分配权重 |
| `TIdsneiList__demo.txt` | 第 1 个开关为 `T` | D8 下游邻居诊断列表；当前代码实际产生双下划线 |
| `TIdscelGrid_demo.tif` | 第 2 个开关为 `T` | D8 下游邻居单元栅格 |
| `TIcelindxGrid_demo.tif` | 第 3 个开关为 `T` | 修正后的计算顺序栅格 |
| `TIcelindxList_demo.txt` | 第 4 个开关为 `T` | 单元号和索引号列表 |
| `TIflodirGrid_demo.tif` | `aif=1` 且第 5 个开关为 `T` | 转换成 TopoIndex 编码的流向栅格 |
| `TIridge_crest_demo.tif` | `pwr >= 0` 且第 6 个开关为 `T` | 山脊单元栅格 |
| `TIgrid_size.txt` | 无流向文件时，或计算得到多下游权重时 | `imax / nrow / ncol / nwf` 参数 |
| `TopoIndexLog.txt` | 正常完成主流程时 | 初始化参数、诊断与运行日志 |

GeoTIFF 使用 `Int32`、LZW 压缩、分块存储，并继承参考栅格的地理变换和投影。

`TIdsneiList__<suffix>.txt` 的双下划线来自当前文件名前缀和格式化表达式的组合；如果下游程序要求官方单下划线命名，应先修正代码并对结果重新验证。

## 从源码构建 Fortran 扩展

构建会覆盖 `topoindex_f2py/` 中同平台的既有扩展文件。请先备份需要保留的二进制。

### Windows

确保当前环境中的 `python`、NumPy、Meson、Ninja 和 gfortran 均可用：

```powershell
python -m pip install "numpy==1.26.4" meson ninja
gfortran --version
python -c "import numpy; print(numpy.__version__)"
.\build_topoindex.cmd
```

构建成功后应能执行：

```powershell
python -c "from topoindex_f2py import topoindex; print(topoindex.__file__)"
```

编译器运行时必须与新生成的 `.pyd` 匹配。不要默认仓库中现有 DLL 与任意 gfortran 版本兼容。

### Linux / macOS

`build_topoindex.sh` 可以生成 `.so`，但当前 `topoindex_f2py/__init__.py` 无条件调用 Windows 专用的 `os.add_dll_directory()`。因此 POSIX 加载路径目前属于未完成适配，不能视为正式支持；需先增加平台判断、重新构建并运行回归测试。

## 常见问题

### `ImportError: DLL load failed while importing topoindex`

常见原因：

- Python 不是 CPython 3.12 x64；
- `.pyd` 与 NumPy、编译器 ABI 不匹配；
- `lib/` 中缺少对应 gfortran 运行时，或混入了其他工具链的同名 DLL；
- GDAL/OSGeo 环境修改了 DLL 搜索顺序。

优先在一个干净环境中重新构建，不建议反复从未知来源复制 DLL。

### 无法读取栅格

确认：

- `from osgeo import gdal` 可正常导入；
- 路径以初始化文件所在目录为基准；
- GDAL 构建包含对应栅格驱动；
- DEM 和流向栅格均为可读的单波段数据。

### `nxtcel failed` 或日志出现 mismatched cells

检查 DEM 与流向栅格是否完全同网格，并确认每个 DEM 有效单元都有合法流向值。仅仅行列数相同还不够。

### 索引修正未收敛

先排查洼地、环路、无效方向和 NODATA 边界问题，再谨慎提高 `itmax`。提高迭代次数不能修复错误的输入拓扑。

## 结果验证建议

用于研究或生产前，至少应完成：

1. 使用 USGS 官方教程数据建立基准结果，并记录所用 TRIGRS/TopoIndex 版本；
2. 比较有效单元数量、下游单元列表、索引顺序和权重文件；
3. 检查同一单元的有效权重之和是否符合预期；
4. 核对 GeoTIFF 的行列数、NODATA、坐标系、分辨率和像元对齐；
5. 对 ESRI 编码转换进行九宫格小样本测试；
6. 固定 Python、NumPy、GDAL、gfortran 和运行时 DLL 的版本及来源；
7. 对正式科研结果进行独立复核，不把一次成功运行等同于模型有效性验证。

## 当前限制

- 仓库没有附带可直接运行的 `tpx_in.txt`、测试数据或自动化测试；
- 预编译模块只面向 CPython 3.12 / Windows x64；
- POSIX 包加载器尚未完成平台兼容；
- `topoindex.py` 的直接运行入口仍含开发者本机路径；
- 部分原始 Fortran 控制流和数值约定被保留，尚未形成完整的行为回归报告；
- 当前没有为本项目新增代码选定统一许可证；
- 已打包 DLL 的精确编译器发行版、对应源码和许可证材料尚未在仓库中完整归档。

## 许可证、署名与发布合规

请先阅读 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。核心原则如下：

1. **保留上游归属。** 明确说明代码改编自 USGS TRIGRS 发行版中的 TopoIndex，并保留 Rex L. Baum / USGS 的作者与来源信息。
2. **不要暗示官方关系。** 本项目不得宣传为 USGS 官方版本、官方维护版本或经过 USGS 批准的产品，也不要在未获授权时使用 USGS 标志。
3. **不要给整个仓库套用错误许可证。** 上游 USGS 部分的公有领域声明不等于本项目新增代码已经自动采用 CC0、MIT 或其他许可证。
4. **为新增代码单独选许可证。** 当前根目录没有覆盖本项目原创修改的 `LICENSE`。仓库维护者应在确认权利归属后自行选择许可证，并明确其适用范围。
5. **谨慎分发二进制。** `lib/` 中的 GCC/Fortran/MCF 运行时及预编译 `.pyd` 需要精确的来源、版本、许可证文本和必要的源码/获取方式。材料不齐全时，最稳妥的公开发布方式是暂不分发这些二进制，让用户从已知工具链自行构建。
6. **依赖各有许可证。** NumPy、GDAL 及 GDAL 的可选依赖不受 USGS 公有领域声明覆盖。

公开可见不等于开源授权。在本项目原创代码的许可证确定之前，第三方不应推定自己获得了复制、修改或再分发这些新增部分的许可。

本节仅用于工程合规提示，不构成法律意见。商业发布、收费服务、跨境分发或组织内部合规要求较高时，应由有资质的法律专业人士审查实际代码来源、提交历史和二进制供应链。

## 引用

在论文、报告或产品中使用本项目时，请至少引用官方 TRIGRS 软件和基础报告，并另外注明使用了本非官方 Python 二次开发版：

```text
Baum, R. L., and Alvioli, M., 2016, TRIGRS version 2.1:
U.S. Geological Survey software release. https://doi.org/10.5066/F7M044QS

Baum, R. L., Savage, W. Z., and Godt, J. W., 2008,
TRIGRS—A Fortran program for transient rainfall infiltration and
grid-based regional slope-stability analysis, version 2.0:
U.S. Geological Survey Open-File Report 2008-1159, 75 p.
https://doi.org/10.3133/ofr20081159
```

建议在方法部分补充本仓库的具体提交号、修改日期、Python/NumPy/GDAL 版本和编译器信息，以保证可复现性。

## 免责声明

本项目按“现状”提供，不提供任何明示或默示保证。地形、水文和边坡稳定性分析对输入数据、参数选择、算法假设和实现细节高度敏感。任何人不得仅凭本软件输出作出生命安全、工程设计、应急响应、土地利用或投资决策。使用者应自行验证结果并承担使用风险。
