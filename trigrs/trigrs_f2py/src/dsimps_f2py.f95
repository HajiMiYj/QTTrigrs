subroutine dsimps(n,h,f,intf)
  implicit none
  integer, parameter :: dp = kind(1d0)
  ! Simpson's 3-point rule, integrated at n successive points
  ! over an interval subdivided into 2n equal segments.
  integer:: i,n
  real (dp):: f(2*n+1)
  real (dp):: h,intf(n+1),sumf,fl,fmid,fr
  sumf=0.d0
  do i=1,n
    fl=f(2*i-1)
    fmid=f(2*i)
    fr=f(2*i+1)
    sumf=sumf+fl+4.d0*fmid+fr
    intf(i+1)=sumf*h/3.d0
  end do
  return
end subroutine dsimps
