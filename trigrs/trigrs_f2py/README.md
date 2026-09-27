# TRIGRS 力学内核（Fortran / f2py）

本包把 USGS **TRIGRS v2.1**（官方源码 `C:\Users\worker306\Desktop\landslides-trigrs\src\TRIGRS`）
中**除 IO 以外的全部力学求解**用 Fortran 重写，并经 `numpy.f2py` 编译成 CPython
扩展 `_trigrs_native.cp312-win_amd64.pyd`，与已完成的 **TopoIndex** f2py 方案
保持一致。

- **Fortran 内核**：`src/` 下按官方 TRIGRS 文件结构拆分的独立文件，
  每个命名 `xxx_f2py.<扩展名>`（如 `savage_f2py.f95`、`flux_f2py.f90`、
  `calerf_f2py.f`）；入口在 `src/trigrs_f2py.f90`（module `trigrs_kernels`，
  唯一对外入口 `trigrs_solve(...)`）。
- **Python 胶水**：`../trigrs_fortran.py`，负责读栅格/径流文件、组织参数、
  调用内核、写回结果。
- **重构后的主程序**：`../Trigrs.py`，只保留 IO（读 `tr_in.txt`、读栅格、
  写结果栅格），力学全部交给内核。

## 已迁移到 Fortran 的过程（与官方 serial 版 `trg` 目标一一对应）

| 分类 | 过程 |
| --- | --- |
| 预处理 | `steady`（稳态入渗率调整）、`rnoff`（径流演算，去掉文件 IO） |
| 饱和求解 | `savage`（单步有限深）、`iverson`（单步无限深）、`satinf`（多步无限深）、`satfin`（多步有限深） |
| 非饱和求解 | `unsinf`（无限深）、`unsfin`（有限深） |
| 辅助 | `flux`、`ivestp`、`pstpi`、`pstpf`、`unsth`、`svgstp`、`compute_wtab`（水位面） |
| 数学 | `calerf`、`derfc`、`dbsct`、`roots`、`dsimps`、`dzero_brac`、`smallt` |

**留在 Python 的 IO**：`trini`（读 `tr_in.txt`）、`srdgrd`/`irdgrd`/`ssizgrd`/
`ssvgrd`/`isvgrd`/`irdswm`/`srdswm`（栅格与径流列表读写）、`TrigrsInputFile`。

## 目录

```text
trigrs_f2py/
├── src/                              Fortran 源（按官方拆分，xxx_f2py.<扩展名>）
│   ├── grids_f2py.f95 / input_vars_f2py.f95 / model_vars_f2py.f95   状态模块
│   ├── calerf_f2py.f / derfc_f2py.f / dbsct_f2py.f / roots_f2py.f  定格式数学辅助
│   ├── dsimps_f2py.f95 / dzero_brac_f2py.f90 / smallt_f2py.f95      数学辅助
│   ├── steady_f2py.f95 / rnoff_f2py.f95                             预处理
│   ├── flux_f2py.f90 / ivestp_f2py.f95 / pstpi_f2py.f95 / pstpf_f2py.f95
│   ├── unsth_f2py.f95 / svgstp_f2py.f95                             求解辅助
│   ├── savage_f2py.f95 / iverson_f2py.f95 / satinf_f2py.f95 / satfin_f2py.f95
│   ├── unsinf_f2py.f95 / unsfin_f2py.f95                            求解器
│   └── trigrs_f2py.f90                 入口（module trigrs_kernels / trigrs_solve）
├── build.py                         构建脚本（f2py + meson）
├── _trigrs_native.pyf               f2py 签名（只暴露 trigrs_solve）
├── __init__.py                      扩展装载器（向上找 lib/ 注册 gfortran 运行时）
└── _trigrs_native.cp312-win_amd64.pyd  编译产物
```

## 构建

需要 Python 3.12（含 `numpy`/`f2py`/`meson`/`ninja`）与 MinGW-w64
（`C:\mingw64\bin` 的 `gfortran`/`gcc` 在 PATH 上）：

```bat
set PATH=C:\mingw64\bin;%PATH%
C:\Users\worker306\.conda\envs\python312\python.exe build.py
```

`build.py` 会自动：生成 `.pyf` 签名 → `f2py -c` 编译 → 复制 `.pyd` 与运行时
DLL 到本目录 → 校验导入。

## 数值约定（与官方一致，供胶水层参考）

- 角度在传入内核前已转为**弧度**：`slo`、`phi`、`slomin`、`slomax`。
- `depth` / `zmax` / `rizero` 传**栅格数值**（正深度、正入渗率）；负标量只是
  “改读栅格”的哨兵，在上层读栅格阶段处理。
- `zo` / `nxt` / `indx` / `dsc` / `dsctr` 按 **Fortran 1 基**。
- 二维结果数组（`p3d`/`fs3d`/`th3d`/`ptran3d`/`pzero3d`）遵循 f2py 转置约定：
  Fortran 的 `(m,n)` 对应 NumPy 的 `(n,m)`，胶水层用 `.T` 转回。

## 内核入口签名

```text
ncc, nccs = trigrs_solve(
    imax, nwf, tx, nmax, flag, nper, spcg, nzs, mmax, nzon, nout, kper, nts,
    uww, zmin, t, dep, czmax, crizero, slomin, slomax, deepz, tinc,
    flowdir, el_or_dep, deepwat,
    outp(8), rodoc, lskip, lany, llus, lps0, unsat0, bkgrof, lpge0,
    ths, thr, alp, dif, c, phi, ks, uws, capt, cri, tsav,
    unsat, igcap, slo, zo, rizero, depth, zmax, elev,
    nxt, indx, dsctr, dsc, wf, ri_flat, ans,
    fsmin, zfmin, pmin, wtab, rik1,
    p3d, fs3d, th3d, ptran3d, pzero3d, dh3d, newdep3d,
    nvu, nv, ro, ir)
```

## 已知边界

- **栅格输出**（`fsmin`/`zfmin`/`pmin`/`wtab`/`rik1` 及径流栅格）已完整接通。
- **`flag<0` 的列表输出**（ijz / Z-P-Fs，`flag -1..-6`）已接通：内核返回
  `p3d`/`fs3d`/`th3d`/`ptran3d`/`pzero3d`/`dh3d`/`newdep3d`，胶水层
  `trigrs_fortran.py` 再按与内核一致的公式补算逐单元 `rikzero`/`beta`/`dcf`/
  `p0zmx` 及输出时刻指针 `ksav`/`tsav`，交由 `Svijz`/`Svlist` 写出列表。
- **`flag -7..-9`（xmdv）** 未实现（与 DizaiGIS4 原有行为一致，原实现亦缺失）。
- 每期径流/入渗率栅格（`rodoc`/`outp(6)`）当前写末次结果；逐期输出需内核
  返回逐期 `ro`/`ir`。
