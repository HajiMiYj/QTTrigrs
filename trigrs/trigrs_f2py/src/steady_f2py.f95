subroutine steady(imx1)
  use grids; use input_vars; use model_vars
  implicit none
  ! Compute initial estimate of Isteady/Ks, rikzero(), and test values.
  integer:: i,acnt,imx1
  real (dp):: b,rslo
  acnt=0
  do i=1,imx1
    if(ks(zo(i))==0.) then
      rikzero(i)=1.
    else
      rikzero(i)=rizero(i)/ks(zo(i))
    end if
  end do
  sumex=0.d0
  do i=1,imx1
    rslo=slo(i)
    b=cos(rslo)*cos(rslo)
    if(rikzero(i)>=b) then
      rikzero(i)=cos(rslo)
      acnt=acnt+1
    end if
    if (depth(i)==0 .and. rizero(i)<0) then
      sumex=sumex-rizero(i)
    end if
  end do
  return
end subroutine steady
