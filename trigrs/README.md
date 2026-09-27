# TRIGRS主程序重写

## 一、计算瞬态降雨入渗和网格化区域边坡稳定性分析

2025-9-11江炳辰重写，用Python重写Trigrs程序，本次更新主要的设计思路在于：主程序只允许调代码和处理基本参数，具体业务分发给其他模块

## 二、源代码参数解读

### 数字类型

- integer, parameter:: ulen=25

  定义常量 ulen=25，后面用来指定数组 u 的长度。u 是文件单元号数组，Fortran 里用于文件读写。

- integer:: grd

  存储整个网格的单元总数（grd=row*col），即格点总数。

- integer:: i,j,k,imx1,mnd

- i, j, k：循环计数器。

- imx1：最大网格单元编号（通常等于 imax）。

- mnd：最小深度或某种默认参数，初始化为6。

- integer:: nodata,sctr,umax,patlen

  nodata：无数据值，表示缺失数据。

  sctr：实际有效数据单元数。

  umax：u 数组中的最大值，常用于文件单元号管理。

  patlen：路径长度，处理文件路径时用。

- integer:: ncol,nrow,u(ulen),maxzo,ncc,nccs

  ncol, nrow：网格的列数和行数。

  u(ulen)：长度为25的整型数组，存储文件单元号（Fortran文件操作时用）。

  maxzo：属性区最大编号（如地质区划分）。

  ncc, nccs：非收敛单元计数，分别用于非饱和区和饱和区。

- integer:: time_incr_ctr

- 时间步计数器，用于记录时间步的编号。

- real:: x1, mnzmx, mndep

  x1：临时实数变量。

  mnzmx：zmax（最大深度）的最小值。

  mndep：depth（水位深度）的最小值。

- real:: outp_incr_min, outp_incr

  outp_incr_min：输出时间间隔的最小值。

  outp_incr：当前输出时间间隔。

- real (double):: newdep, dh

  newdep：新的深度值，通常用于输出或中间计算。

  dh：水头变化量，常用于水力计算。

这些变量和常量主要用于：

- 网格和数据文件的管理（如 u、ncol、nrow、grd、patlen）
- 循环和数据处理（i, j, k, imx1, mnd）
- 物理量的存储和计算（x1, mnzmx, mndep, newdep, dh）
- 结果输出和异常处理（ncc, nccs, umax, nodata, sctr, outp_incr_min）

### 字符类型

- character (len=1):: tb

  单字符变量，通常用作制表符（tab），如 tb=char(9)。

- character (len=255):: outfil, infil

  文件名字符串，outfil 表示输出文件名，infil 表示输入文件名。

- character (len=14):: fminfil='TRfs_min_'

  最小安全系数输出文件的前缀名。

- character (len=14):: zfminfil='TRz_at_fs_min_'

  最小安全系数对应深度输出文件的前缀名。

- character (len=14):: pminfil='TRp_at_fs_min_'

  最小安全系数对应压力头输出文件的前缀名。

- character (len=8):: wtabfil='TRwater_'

  水位表输出文件的前缀名。

- character (len=18):: profil='TRlist_z_p_fs_'

  剖面输出文件的前缀名（如高程、压力头、安全系数等列表）。

- character (len=14):: header(6)

  长度为14的字符串数组，存储文件头信息（如输出文件的表头）。

- character (len=13):: ncvfil='TRnon_convrg_'

  非收敛单元输出文件的前缀名。

- character (len=8):: date

  日期字符串，存储当前日期。

- character (len=10):: time

  时间字符串，存储当前时间。

- character (len=4):: stp

  步数或编号字符串，常用于输出文件名中表示第几步。

- character (len=31):: scratch, irfil

  临时字符串变量，scratch 用于临时拼接，irfil 用于输出流量等文件名。

- character (len=7):: vrsn

  版本号字符串。

- character (len=11):: bldate

  编译或版本日期字符串。

- character (len=2):: pid(3)

  长度为2的字符串数组，存储不同类型的文件或网格的标识（如 'TI', 'GM', 'TR'）。

## 三、模块分析

```bat
Jbc_process
│  ├─TrigrsIO # 自定义有关于文件输入输出的模块
│  │
│  ├─TrigrsModule # trigrs模块模块文件重构的类文件，命名与官方文件一致
│  │ 
│  └─TrigrsSubroutine # trigrs子程序重构的python文件，命名与官方文件一致
│    
└─test.py # 主程序
```

