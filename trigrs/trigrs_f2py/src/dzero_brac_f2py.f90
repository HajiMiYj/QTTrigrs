subroutine dzero_brac(nstp,x,zroctr,zrptr)
  implicit none
  integer, parameter :: dp = kind(1d0)
  ! Bracket locations of zero in a list of values by sign change.
  integer:: n,nstp,zroctr,zrptr(nstp+1)
  real (dp):: x(nstp+1)
  zroctr=0; zrptr=0
  do n=1,nstp+1
    if(x(n)==0.d0) then
      zroctr=zroctr+1
      zrptr(n)=2
    end if
  end do
  do n=1,nstp
    if(x(n)*x(n+1)<0.d0) then
      zroctr=zroctr+1
      zrptr(n)=1
    end if
  end do
end subroutine dzero_brac
