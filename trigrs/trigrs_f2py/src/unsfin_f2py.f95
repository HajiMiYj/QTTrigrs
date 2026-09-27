subroutine unsfin(imx1,ncc,nccs)
  use grids; use input_vars; use model_vars
  implicit none
  integer::i,j,jf,k,imx1,ncc,nccs,nmx,nmax0
  integer::nmn1,nmin1,nmax3,nmxp,nmxs,nmnp,nmns
  integer:: svgctr
  logical:: lcv,lcvs,lwt
  real:: delwt,dwt,zwt,qbij(nts+1)
  real::tolqk
  real (dp)::rf(nzs+1),finf,vqt,qta,al,qzmax
  real (dp)::ddwt,sqin,intq(nts+1),b,dhwt(nts+1),delh
  real (dp)::qtn(2*nts+1),intq1(nts+1),vqtn,cd
  nmax3=0;nmax0=0
  nmn1=nmax+1;nmin1=nmax+1
  nmxp=0; nmnp=0; svgctr=0; nmns=0; nmxs=0
  intq=0.d0; intq1=0.d0
  finf=10.
  grid_loop: do i=1,imx1
    if(slo(i)<slomin .or. slo(i)>slomax .or. zmax(i)<=0.0001) then
      do jf=1,nout
        fsmin(i+(jf-1)*imax)=finf+1.
        zfmin(i+(jf-1)*imax)=zmax(i)
        pmin(i+(jf-1)*imax)=0.
      end do
      cycle
    end if
    lcv=.true.;lcvs=.true.
    q=0.;qb=0
    tolqk=ks(zo(i))*5.e-07
    do j=1,kper
      if(j>nper) then
        q(j)=0.
      else
        if(bkgrof) then
          q(j)=ks(zo(i))*(rik(i+(j-1)*imax)+rikzero(i))
        else
          q(j)=ks(zo(i))*rik(i+(j-1)*imax)
          tolqk=ks(zo(i))*5.e-07
        end if
      end if
    end do
    qmax=maxval(q)
    b=cos(slo(i))
    if(unsat(zo(i))) then
      dcf=depth(i)-1.d0/(alp(zo(i)))
    else
      dcf=0.
    end if
    if(lps0 .and. unsat(zo(i))) then
      dusz=depth(i)-1.d0/(alp(zo(i)))
    else
      dusz=depth(i)
    end if
    cd=0.1d0
    select case (flowdir)
      case ('slope')
        beta=b*b
        qzmax=(1.d0-beta)*cd*ks(zo(i))
      case ('hydro')
        beta=1.d0
        qzmax=0.d0
      case default
        beta=b*b-rikzero(i)
        qzmax=(1.d0-beta)*cd*ks(zo(i))-cd*rizero(i)
    end select
    delwt=0.;dwt=depth(i);zwt=depth(i);ddwt=depth(i)
    lwt=.false.
    ts=tmin
    if(dcf>0. .and. (unsat(zo(i)) .or. igcap(zo(i)))) then
      vqt=0.;vqtn=0.;qta=rizero(i);sqin=0.
      al=alp(zo(i))*b*b
      call roots(nmax,r,dusz,al,eps,pi)
      flux_loop: do j=1,2*nts+1
        call flux(i,kper,ts,j,lcv,ncc,nvu(i),lwt)
        if(nmax1>nmax2) nmax2=nmax1
        if(nmn<nmin) nmin=nmn
        if(qt<rizero(i)) qt=rizero(i)
        if(bkgrof) then
          if(qt>ks(zo(i))+rizero(i)+tolqk) then
            qt=ks(zo(i))
          end if
        else
          if(qt>ks(zo(i))+tolqk) then
            qt=ks(zo(i))
          end if
        end if
        if(qt>qzmax) then
          qtime(j)=qt-qzmax
        else
          qtime(j)=0.d0
        end if
        qtn(j)=qt
        qta=qt
        ts=ts+tinc/2.d0
      end do flux_loop
      call dsimps(nts,tinc/2.d0,qtime,intq)
      call dsimps(nts,tinc/2.d0,qtn,intq1)
      ts=tmin
      wt_rise_loop: do j=1,nts+1
        jf=jsav(j)
        rf=0.0
        vqt=intq(j)-ts*rizero(i)
        if(vqt<0.) vqt=0.d0
        vqtn=intq1(j)-ts*rizero(i)
        sqin=0.
        sum_q_in_loop: do k=1,nper
          if(ts>capt(k) .and. ts<=capt(k+1)) then
            qts(j)=q(k)
          endif
          if(ts>=capt(k+1)) then
            sqin=sqin+(capt(k+1)-capt(k))*q(k)
          end if
          if(ts>capt(k) .and. ts<capt(k+1)) then
            sqin=sqin+(ts-capt(k))*q(k)
          end if
        end do sum_q_in_loop
        if(jf>0 .and. lskip) then
          call unsth(i,j,ncc,kper,ts,nmax0,lcv,vqt,delh,nmn1,sqin,vqtn)
          dhwt(j)=delh
          if(nmax0>nmax3) nmax3=nmax0
          if(nmn1<nmin1) nmin1=nmn1
        else if(lskip) then
          continue
        else
          call unsth(i,j,ncc,kper,ts,nmax0,lcv,vqt,delh,nmn1,sqin,vqtn)
          dhwt(j)=delh
          if(nmax0>nmax3) nmax3=nmax0
          if(nmn1<nmin1) nmin1=nmn1
        end if
        tcap(j)=ts
        tcap(j+1)=ts+tinc
        ts=ts+tinc
        if(jf>0 .and. lskip) then
          call pstpf(dhwt,dwt,i,j-1,rf,nccs,lcvs,nmx,tcap(j),jf)
          nmxp=nmx;nmnp=nmn
          if(j>1) then
            delwt=abs(dwt-zwt)*1000.
            if(delwt>dwt) then
              lwt=.true.
              dwt=zwt
            end if
          end if
        else if(lskip) then
          continue
        else
          call pstpf(dhwt,dwt,i,j-1,rf,nccs,lcvs,nmx,tcap(j),jf)
          nmxp=nmx;nmnp=nmn
          if(j>1) then
            delwt=abs(dwt-zwt)*1000.
            if(delwt>dwt) then
              lwt=.true.
              dwt=zwt
            end if
          end if
        end if
      end do wt_rise_loop
      do k=1,nts
        qb(k)=qtime(2*k+1)
        if(outp(7)) rik1(i+(k-1)*imax)=qb(k)/ks(zo(i))
      end do
    else
      qb=0.
      dwt=depth(i)
      delh=0.;rf=0.;zwt=depth(i)
      do j=1,nts+1
        do k=1,kper
          if(ts>=capt(k) .and. ts<=capt(k+1)) qb(j)=q(k)
        end do
        if(outp(7)) rik1(i+(j-1)*imax)=qb(j)/ks(zo(i))
        tcap(j)=ts
        ts=ts+tinc
      end do
      do j=1,nts+1
        qbij(j)=qb(j)/ks(zo(i))
      end do
      rf=0.
      svgctr=svgctr+1
      call svgstp(qbij,i,rf,nccs,lcvs,nmxs)
      nmns=nmn
    end if
  end do grid_loop
  if(nmin>nmax2) nmin=nmax2; if(nmin1>nmax3) nmin1=nmax3
  if(nmnp>nmxp) nmnp=nmxp; if(nmns>nmxs) nmns=nmxs
  return
end subroutine unsfin
