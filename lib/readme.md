You need the following .dll files, which can be obtained from folders such as mingw64:

你需要以下.dll，可以从mingw64等文件夹中取得：

- libgcc_s_seh-1.dll
- libgfortran-5.dll
- libmcfgthread-2.dll
- libquadmath-0.dll
- libwinpthread-1.dll

本目录是 QTTrigrs 中两个 Fortran(f2py) 内核（TopoIndex 与 TRIGRS）共用的
gfortran 运行时，两个装载器都会沿目录树向上查找本 ``lib/`` 并自动注册。
