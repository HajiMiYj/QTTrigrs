subroutine ivestp(rikf,i,rf)
  use grids; use input_vars; use model_vars
  implicit none
  real(dp) :: derfc
  ! Iverson's method, time series (infinite-depth saturated zone).
  integer:: i,j,jf,n,nn
  real:: rikf(nts+1),finf
  real (dp):: a1,b1,ff,zns,zinc,z,t0,znew
  real (dp):: zstar,tstar,x1,x2,x3,x4
  real (dp):: rf1,rf2,rf3,rf4,rfa,rfb,rf(nzs+1)
  real (dp):: fs,rslo,rphi,fmn,ptest,pmn,dhat
  real (dp):: captstar1,captstar2,tdif1,tdif2
  real (dp):: dusz1,newdep
  pi=3.141592653589793
  finf=10.
  rslo=slo(i)
  rphi=phi(zo(i))
  a1=sin(rslo)
  b1=cos(rslo)
  dhat=4.*dif(zo(i))/(b1*b1)
  p0zmx=0.
  newdep=-9999.
  select case (flowdir)
    case ('slope')
      beta=b1*b1
    case ('hydro')
      beta=1.d0
    case default
      beta=b1*b1-rikzero(i)
  end select
  if(abs(b1-rikzero(i))<1.e-6) beta=0.d0
  if (abs(rslo)>1.e-5) then
    ff=tan(rphi)/tan(rslo)
  else
    ff=finf
  end if
  zns=float(nzs)
  zinc=(zmax(i)-zmin)/zns
  dusz1=0.
  ptran=0.
  temporal_loop: do n=1,nts+1
    t0=tcap(n)
    fmn=1.e25
    jf=jsav(n)
    z=zmin
    Z_loop: do j=1,nzs+1
      znew=z
      if(znew < 1.0e-30) znew =1.0e-30
      if (abs(a1)>1.e-5) then
        fc(j)=c(zo(i))/(uws(zo(i))*znew*a1*b1)
      else
        fc(j)=0.d0
      end if
      pzero(j)=beta*(z-depth(i))
      if(z<dusz1) then
        rf(j)=0.0
      else
        rf(j)=0.0
        if (abs(z)>0.) then
          zstar=z**2/dhat
          tstar=t0/zstar
        end if
        temporal_loop_1: do nn=1,nper
          if(z==0.) then
            tdif1=t0-capt(nn)
            if(tdif1>0.) then
              rfa=sqrt(tdif1*dhat/pi)
            else
              rfa=0.0
            end if
            tdif2=t0-capt(nn+1)
            if(tdif2>0.) then
              rfb=sqrt(tdif2*dhat/pi)
            else
              rfb=0.0
            end if
          else
            captstar1=capt(nn)/zstar
            tdif1=tstar-captstar1
            if(tdif1 > 0.0) then
              x1=1./tdif1
              x2=1./(sqrt(tdif1))
              rf1=sqrt(1./(x1*pi))*exp(-x1)
              rf2=derfc(x2)
              rfa=rf1-rf2
            else
              rfa=0.0
            end if
            captstar2=capt(nn+1)/zstar
            tdif2=tstar-captstar2
            if(tdif2 > 0.0) then
              x3=1./tdif2
              x4=1./(sqrt(tdif2))
              rf3=sqrt(1./(x3*pi))*exp(-x3)
              rf4=derfc(x4)
              rfb=rf3-rf4
            else
              rfb=0.0
            end if
          end if
          rf(j)=rf(j)+rik(i+(nn-1)*imax)*(rfa-rfb)
          if(rfa==0.0 .and. rfb==0.0) exit
        end do temporal_loop_1
      end if
      bline(j)=z*beta
      if(abs(rf(j))>0.0) then
        ptran(j)=z*rf(j)
        if(z==0) ptran(j)=rf(j)
      end if
      p(j)=pzero(j)+ptran(j)
      ptest=p(j)-bline(j)
      if(ptest > 0.0) then
        p(j)=bline(j)
      end if
      z=z+zinc
    end do Z_loop
    if(n==1) p0zmx=p(nzs+1)
    if(rikzero(i)<0.0) then
      zinc=(zmax(i)-zmin)/zns
      z=zmin
      newdep=0.0
      do j=1,nzs+1
        if(p(j)<0.0) newdep=z
        z=z+zinc
      end do
      z=zmin
      do j=1,nzs+1
        if(p(j)>0.0 .and. z<newdep) p(j)=0.d0
        if(p(j)>=0.0 .and. z>=newdep) p(j)=beta*(z-newdep)
        z=z+zinc
      end do
    end if
    z=zmin
    Z_FS_loop: do j=1,nzs+1
      if (abs(a1)>1.e-5 .and. z>1.e-30) then
        if(lpge0 .and. p(j)<0.) then
          fw(j)=0.d0
        else
          fw(j)=-(p(j)*uww*tan(rphi))/(uws(zo(i))*z*a1*b1)
        end if
      else
        fw(j)=0.d0
      end if
      fs=ff+fw(j)+fc(j)
      if ((ff+fw(j))<0.) fs=fc(j)
      if (fs>finf) fs=finf
      if (z<=1.e-02) fs=finf
      if(jf>0) then
        if (fs<fmn) then
          fmn=fs
          zfmin(i+(jf-1)*imax)=z
          pmn=p(j)
        end if
        if(flag<0 .or. outp(1)) then
          p3d(i+(jf-1)*imax,j)=p(j)
          newdep3d(i+(jf-1)*imax)=newdep
          dh3d(i+(jf-1)*imax)=0.d0
        end if
        if(flag==-1) fs3d(i+(jf-1)*imax,j)=fs
        if(flag==-2) then
          fs3d(i+(jf-1)*imax,j)=fs
          ptran3d(i+(jf-1)*imax,j)=ptran(j)
          pzero3d(i,j)=pzero(j)
        end if
        if(flag==-3) then
          fs3d(i+(jf-1)*imax,j)=fs
          th3d(i+(jf-1)*imax,j)=ths(zo(i))
        end if
        if(flag<=-4 .or. outp(1)) th3d(i+(jf-1)*imax,j)=ths(zo(i))
      end if
      z=z+zinc
    end do Z_FS_loop
    if (jf>0) then
      fsmin(i+(jf-1)*imax)=fmn
      if(fmn==finf) then
        pmn=p(nzs+1)
        zfmin(i+(jf-1)*imax)=zmax(i)
      end if
      if(lpge0 .and. pmn<0.) then
        pmin(i+(jf-1)*imax)=0.
      else
        pmin(i+(jf-1)*imax)=pmn
      end if
    end if
  end do temporal_loop
  return
end subroutine ivestp
