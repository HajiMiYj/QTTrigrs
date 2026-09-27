subroutine iverson(imx1)
  use grids; use input_vars; use model_vars
  implicit none
  real(dp) :: derfc
  ! Iverson's (2000) method, infinite-depth saturated zone (single step).
  integer:: j,i,imx1,n,mils
  real:: finf
  real (dp) :: a1,b1,ff,zns,zinc,z,znew
  real (dp) :: zstar,tstar,x1,x2,x3,x4
  real (dp) :: rf1,rf2,rf3,rf4,rfa,rfb,rf
  real (dp) :: fs,rslo,rphi,fmn,ptest,pmn,dhat
  real (dp) :: newdep,captstar1,captstar2,tdif1,tdif2
  pi=3.141592653589793
  dg2rad=pi/180.D0
  finf=10.
  mils=imax/1000
  grid_loop: do i=1,imx1
    rslo=slo(i)
    if(rslo<slomin .or. rslo>slomax .or. zmax(i)<=0.0001) then
      fsmin(i)=finf+1.
      zfmin(i)=zmax(i)
      pmin(i)=0.
      cycle grid_loop
    end if
    rphi=phi(zo(i))
    a1=sin(rslo)
    b1=cos(rslo)
    dhat=4.*dif(zo(i))/(b1*b1)
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
    z=zmin
    fmn=1.e25
    rf=0.0
    z_loop: do j=1,nzs+1
      znew=z
      if(znew < 1.0e-30) znew =1.0e-30
      if (abs(a1)>1.e-5) then
        fc(j)=c(zo(i))/(uws(zo(i))*znew*a1*b1)
      else
        fc(j)=0.d0
      end if
      pzero(j)=beta*(z-depth(i))
      if (abs(z)>0.) then
        zstar=z**2/dhat
        tstar=t/zstar
      end if
      rf=0.0
      temporal_loop: do n=1,nper
        if(z==0.) then
          tdif1=t-capt(n)
          if(tdif1>0.) then
            rfa=sqrt(tdif1*dhat/pi)
          else
            rfa=0.0
          end if
          tdif2=t-capt(n+1)
          if(tdif2>0.) then
            rfb=sqrt(tdif2*dhat/pi)
          else
            rfb=0.0
          end if
        else
          captstar1=capt(n)/zstar
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
          captstar2=capt(n+1)/zstar
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
        rf=rf+rik(i+(n-1)*imax)*(rfa-rfb)
        if(rfa==0.0 .and. rfb==0.0) exit
      end do temporal_loop
      ptran(j)=z*rf
      if(z==0) ptran(j)=rf
      p(j)=pzero(j)+ptran(j)
      bline(j)=z*beta
      ptest=p(j)-bline(j)
      if(ptest > 0.0) then
        p(j)=bline(j)
      end if
      if (abs(a1)>1.e-5) then
        if(lpge0 .and. p(j)<0.) then
          fw(j)=0.d0
        else if (z>0.) then
          fw(j)=-(p(j)*uww*tan(rphi))/(uws(zo(i))*z*a1*b1)
        end if
      else
        fw(j)=0.d0
      end if
      z=z+zinc
    end do z_loop
    if(rikzero(i)<0.0) then
      zinc=(zmax(i)-zmin)/zns
      z=zmin
      newdep=0.0
      z_loop_a: do j=1,nzs+1
        if(p(j)<0.0) newdep=z
        z=z+zinc
      end do z_loop_a
      z=zmin
      z_loop_b: do j=1,nzs+1
        if(p(j)>0.0 .and. z<newdep) p(j)=0.d0
        if(p(j)>=0.0 .and. z>=newdep) p(j)=beta*(z-newdep)
        z=z+zinc
      end do z_loop_b
    end if
    z=zmin
    fs_loop: do j=1,nzs+1
      fs=ff+fw(j)+fc(j)
      if ((ff+fw(j))<0.) fs=fc(j)
      if (fs>finf) fs=finf
      if (z<=1.e-02) fs=finf
      if (fs<fmn) then
        fmn=fs
        zfmin(i)=z
        pmn=p(j)
      end if
      if(flag<0 .or. outp(1)) then
        p3d(i,j)=p(j)
        newdep3d(i)=newdep
        dh3d(i)=0.d0
      end if
      if(flag==-1) fs3d(i,j)=fs
      if(flag==-2) then
        fs3d(i,j)=fs
        ptran3d(i,j)=ptran(j)
        pzero3d(i,j)=pzero(j)
      end if
      if(flag==-3) then
        fs3d(i,j)=fs
      end if
      if(flag<=-4 .or. outp(1)) th3d(i,j)=ths(zo(i))
      z=z+zinc
    end do fs_loop
    fsmin(i)=fmn
    if(fmn==finf) then
      pmn=p(nzs+1)
      zfmin(i)=zmax(i)
    end if
    if(lpge0 .and. pmn<0.) then
      pmin(i)=0.
    else
      pmin(i)=pmn
    end if
  end do grid_loop
  return
end subroutine iverson
