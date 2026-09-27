subroutine flux(ic,iper,t0,j1,lcv,ncc,nv0,lwt)
  use grids; use input_vars; use model_vars
  implicit none
  integer:: ic
  integer:: j1,iper,i,k,k1,ncc,nv0
  real (dp):: al,qa,tol
  real (dp):: t0,tf,q1a,q1b,q2a,q2b,qta,qtb,qtop
  real (dp):: q2old,delq2,tdif1,tdif2,tstar
  real (dp):: q0a,q0b
  real (dp):: z,psih,qlb,ck,th,b1
  real (dp):: bot(nmax),qtops(nmax),dseep
  logical:: lcv,lwt
  tol=1.0e-06
  b1=cos(slo(ic))
  al=alp(zo(ic))*b1*b1
  qa=rizero(ic)
  tf=al*ks(zo(ic))/(ths(zo(ic))-thr(zo(ic)))
  qt=0.0; qta=0.0; qtb=0.0
  nmax1=0
  nmn=nmax+1
  do k=1,nmax
    bot(k)=1.+al*dusz/2.+2.*al*dusz*r(k)**2
    qtops(k)=r(k)*sin(r(k)*al*dusz)
  end do
  flux_time_loop: do  i=1,iper
    tdif1=t0-capt(i)
    if (tdif1 < 0.) exit
    if(tdif1 > 0.0) then
      tstar=tf*tdif1
      if(tstar < smt) then
        z=dusz
        qlb=ks(zo(ic))
        call smallt(tstar,al,qa,q(i),dusz,qlb,ths(zo(ic)),thr(zo(ic)),qta,psih,ck,th,z)
        nmn=1
      else
        q2a=0.0
        do k=1,nmax
          qtop=qtops(k)*exp(-(r(k)**2)*tstar)
          q2old=q2a
          q2a=q2a+qtop/bot(k)
          delq2=abs(q2a-q2old)/ks(zo(ic))
          k1=k
          if(abs(q2a)<=tol .and. k>3) exit
          if(delq2<=tol) exit
        end do
        if(lcv) then
          if((delq2>tol) .and. (abs(q2a)>tol .and. k>3)) then
            ncc=ncc+1
            nv0=1
            lcv=.false.
          end if
        end if
        if(k1>nmax1) nmax1=k1
        if(k1<nmn) nmn=k1
        q0a=q(i)
        q1a=4.d0*(q(i)-qa)*exp(al*dusz/2.)
        qta=q0a-q1a*q2a*exp(-tstar/4.)
      end if
    else
      qta=0.0
    end if
    tdif2=t0-capt(i+1)
    if(tdif2 > 0.0) then
      tstar=tf*tdif2
      if(tstar < smt) then
        z=dusz
        qlb=ks(zo(ic))
        call smallt(tstar,al,qa,q(i),dusz,qlb,ths(zo(ic)),thr(zo(ic)),qtb,psih,ck,th,z)
        nmn=1
      else
        q2b=0.0
        do k=1,nmax
          qtop=qtops(k)*exp(-(r(k)**2)*tstar)
          q2old=q2b
          q2b=q2b+qtop/bot(k)
          delq2=abs(q2b-q2old)/ks(zo(ic))
          k1=k
          if(abs(q2b)<=tol .and. k>3) exit
          if(delq2<=tol) exit
        end do
        if(lcv) then
          if((delq2>tol) .and. (abs(q2b)>tol .and. k>3)) then
            ncc=ncc+1
            nv0=1
            lcv=.false.
          end if
        end if
        if(k1>nmax1) nmax1=k1
        if(k1<nmn) nmn=k1
        q0b=q(i)
        q1b=4.d0*(q(i)-qa)*exp(al*dusz/2.)
        qtb=q0b-q1b*q2b*exp(-tstar/4.)
      end if
    else
      qtb=0.0
    end if
    qt=qt+qta-qtb
  end do flux_time_loop
  if(qmax<qt .or. qt<0) then
    dseep=ks(zo(ic))/(ths(zo(ic))*t0)
    if(dseep < dusz) then
      qt=0.d0
    end if
  end if
  return
end subroutine flux
