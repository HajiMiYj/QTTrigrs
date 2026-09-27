module model_vars
  implicit none
  integer, parameter :: dp = kind(1d0)
  integer :: nts, kper, nmax1, nmax2, nmn, nmin
  integer, allocatable :: jsav(:)
  real :: dg2rad
  real, allocatable :: q(:), qb(:)
  real(dp) :: eps, tmin, tmax, ts, qt, tns, beta, qmax, tinc
  real(dp) :: sumex, dusz, dcf, vf0, p0zmx
  real(dp) :: ti, tis, pi, smt, lard
  real(dp), allocatable :: p(:), ptran(:), pzero(:), bline(:), chi(:)
  real(dp), allocatable :: r(:), fc(:), fw(:), thz(:), kz(:), tcap(:), tinc_sat(:)
  real(dp), allocatable :: trz(:), uwsp(:), gs(:), qtime(:), qts(:)
  real(dp), allocatable :: p3d(:,:), pzero3d(:,:), ptran3d(:,:), fs3d(:,:), th3d(:,:)
  real(dp), allocatable :: dh3d(:), newdep3d(:)
end module model_vars
