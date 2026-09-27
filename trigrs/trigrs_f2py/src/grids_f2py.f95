module grids
  implicit none
  integer, allocatable :: indx(:), nxt(:), nv(:), nvu(:)
  integer, allocatable :: dsctr(:), dsc(:), zo(:)
  real, allocatable :: rikzero(:)
  real, allocatable :: rik(:), rik1(:), ri(:), ri_all(:), rizero(:)
  real, allocatable :: ro(:), wf(:), ir(:)
  real, allocatable :: zmax(:), slo(:), depth(:)
  real, allocatable :: zfmin(:), fsmin(:), pmin(:)
  real, allocatable :: elev(:), wtab(:)
end module grids
