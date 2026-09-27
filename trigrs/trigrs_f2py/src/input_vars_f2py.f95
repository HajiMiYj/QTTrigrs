module input_vars
  implicit none
  logical :: ans, outp(8), rodoc, lskip, lany, llus, lps0, unsat0, bkgrof
  logical :: lpge0
  logical, allocatable :: unsat(:), igcap(:)
  integer :: imax, nwf, tx, nmax
  integer :: flag, nper, spcg, nzs, mmax, nzon, nout
  integer, allocatable :: ksav(:)
  real :: uww, zmin, t, dep, czmax, crizero, slomin, slomax, deepz
  real, allocatable :: ths(:), thr(:), alp(:), dif(:), c(:), phi(:)
  real, allocatable :: ks(:), uws(:), capt(:), cri(:), tsav(:)
  character(len=5) :: flowdir, el_or_dep
  character(len=4) :: deepwat
end module input_vars
