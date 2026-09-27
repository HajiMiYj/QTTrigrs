subroutine satfin(imx1,nccs)
  use grids; use input_vars; use model_vars
  implicit none
  ! time series, fully saturated case, finite-depth (calls svgstp).
  integer::i,j,jf,k,imx1,nccs
  integer::nmn1,nmin1,nmax3,nmxs,nmns,nmax0
  logical:: lcvs
  real:: qbij(nts+1)
  real (dp)::rf(nzs+1),finf
  nmax3=0;nmax0=0;nmxs=0
  nmn1=nmax+1;nmin1=nmax+1
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
    lcvs=.true.
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
    call svgstp(qbij,i,rf,nccs,lcvs,nmxs)
    nmns=nmn
  end do
  if(nmns>nmxs) nmns=nmxs
  return
end subroutine satfin
