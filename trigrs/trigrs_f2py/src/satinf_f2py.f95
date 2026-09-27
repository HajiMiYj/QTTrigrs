subroutine satinf(imx1,nccs)
  use grids; use input_vars; use model_vars
  implicit none
  ! time series, fully saturated case, infinite-depth (calls ivestp).
  integer::i,j,jf,k,imx1,nccs
  real:: qbij(nts+1)
  real (dp)::rf(nzs+1),finf
  finf=10.
  do i=1,imx1
    if(slo(i)<slomin .or. slo(i)>slomax .or. zmax(i)<=0.0001) then
      do jf=1,nout
        fsmin(i+(jf-1)*imax)=finf+1.
        zfmin(i+(jf-1)*imax)=zmax(i)
        pmin(i+(jf-1)*imax)=0.
      end do
      cycle
    end if
    q=0.
    do j=1,kper
      if(j>nper) then
        q(j)=0.
      else
        q(j)=ks(zo(i))*rik(i+(j-1)*imax)
      end if
    end do
    qb=0.
    ts=0.
    do j=1,nts+1
      do k=1,kper
        if(ts>=capt(k) .and. ts<=capt(k+1)) qb(j)=q(k)
      end do
      if(outp(7)) rik1(i+(j-1)*imax)=qb(j)/ks(zo(i))
      tcap(j)=ts
      ts=ts+tinc_sat(j)
    end do
    do j=1,nts+1
      qbij(j)=qb(j)/ks(zo(i))
    end do
    rf=0.
    call ivestp(qbij,i,rf)
  end do
  return
end subroutine satinf
