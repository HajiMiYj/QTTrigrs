subroutine pstpi(dhwt,dwt,i,iper,rf,t0,jf)
  use grids; use input_vars; use model_vars
  implicit none
  real(dp) :: derfc
  ! diffusion model for pressure head from rising water table (infinite).
  integer:: i,j,jf,m,iper,jmark,nstp,jtop
  real:: dwt
  real (dp):: finf,t1,t2,term1,term2,znew,t0
  real (dp):: ferfc1,ferfc3,dhwt(nts+1),dh
  real (dp):: a1,b1,zns,zinc,tdif1,tdif2,z,newdep
  real (dp):: ar1,ar3,fs,rf(nzs+1)
  real (dp):: rfa,rfb,ff,rslo,rphi,fmn,ptest
  real (dp):: tol
  real (dp):: dusz0,dusz1,dlz,d1,zm
  real (dp):: uwt1,uwsum
  pi=3.141592653589793
  finf=10.
  nmn=1+mmax
  tol=1.e-06
  dh=dhwt(iper+1)
  rslo=slo(i)
  rphi=phi(zo(i))
  a1=sin(rslo)
  b1=cos(rslo)
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
  nstp=int((1./alp(zo(i))/zinc))
  z=zmin
  fmn=1.e25
  if(unsat(zo(i))) then
    if(lps0) then
      dusz0=depth(i)-1./alp(zo(i))
    else
      dusz0=depth(i)
    end if
    dusz1=dwt-1./alp(zo(i))
  else
    dusz0=0.
    dusz1=0.
  end if
  dlz=zmax(i)-dusz0
  zm=zmax(i)
  uwsum=0.
  uwsp=uws(zo(i))
  rf=0.0
  jmark=1
  Z_loop: do j=1,nzs+1
    znew=z
    if(z<depth(i))then
      jmark=j
    end if
    if(znew < 1.0e-30) znew =1.0e-30
    pzero(j)=beta*(z-depth(i))
    if(z <= depth(i))then
      pzero(j)=0.
      if(lps0) then
        if(llus) then
          if(z > dusz0-dh .and. z < depth(i)-dh) then
            rf(j)=(-1./alp(zo(i))+(z-dusz0+dh))
          else if(z >= depth(i)-dh) then
            rf(j)=beta*(z-depth(i)+dh)
          else
            rf(j)=ptran(j)
          end if
        else
          if(z > dusz0 .and. z < depth(i)) then
            rf(j)=(-1./alp(zo(i))+(z-dusz0))
          else if(z >= depth(i)) then
            rf(j)=beta*(z-depth(i))
          else
            rf(j)=ptran(j)
          end if
        end if
      else
        if(z >= dusz0-dh .and. llus) then
          rf(j)=beta*(z+dh-dusz0)
        else
          rf(j)=ptran(j)
        end if
      end if
    else if(z>=zm .and. dlz<0.001) then
      rf(j)=beta*(z+dh-dusz0)
    else if(llus) then
      temporal_loop: do m=1,iper
        tdif1=t0-tcap(m)
        if(tdif1 > 0.0) then
          d1=dif(zo(i))/(b1*b1)
          t1=sqrt(d1*tdif1)
          if (t1<1.0e-29) t1=1.0e-29
          term1=0.0
          ar1=(z-dusz0)/(2.*t1)
          ferfc1=derfc(ar1)
          term1=ferfc1
          rfa=term1
        else
          rfa=0.0
        end if
        tdif2=t0-tcap(m+1)
        if(tdif2 > 0.0) then
          d1=dif(zo(i))/(b1*b1)
          t2=sqrt(d1*tdif2)
          if (t2<1.0e-29) t2=1.0e-29
          term2=0.0
          ar3=(z-dusz0)/(2.*t2)
          ferfc3=derfc(ar3)
          term2=ferfc3
          rfb=term2
        else
          rfb=0.0
        end if
        rf(j)=rf(j)+dh*beta*(rfa-rfb)
        if(rfa==0.0 .and. rfb==0.0) exit
      end do temporal_loop
    end if
    bline(j)=z*beta
    ptran(j)=rf(j)
    p(j)=pzero(j)+ptran(j)
    ptest=p(j)-bline(j)
    if(ptest > 0.0) then
      p(j)=bline(j)
    end if
    if(p(j)<-1.d0/alp(zo(i))) then
      uwt1=(gs(zo(i))*(1-ths(zo(i)))+thz(j))*uww
    else
      uwt1=uws(zo(i))
    end if
    uwsum=uwsum+uwt1
    uwsp(j)=uwsum/float(j)
    z=z+zinc
  end do Z_loop
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
  if(llus .and. zm>depth(i)) then
    jtop=jmark-nstp
    if(jtop<1) jtop=1
    do j=jmark,jtop,-1
      if(ptran(j)>ptran(j+1)) then
        ptran(j)=ptran(j+1)
        p(j)=ptran(j)+pzero(j)
      end if
    end do
  end if
  z=zmin
  Z_FS_loop: do j=1,nzs+1
    chi(j)=1.0
    if(p(j)<0.) then
      chi(j)=(thz(j)-thr(zo(i)))/(ths(zo(i))-thr(zo(i)))
    else
      chi(j)=1.0; thz(j)=ths(zo(i))
    end if
    if (abs(a1)>1.e-5 .and. z>0.) then
      fw(j)=-(chi(j)*p(j)*uww*tan(rphi))/(uwsp(j)*z*a1*b1)
      fc(j)=c(zo(i))/(uwsp(j)*z*a1*b1)
    else
      fw(j)=0.d0
      fc(j)=0.d0
    end if
    fs=ff+fw(j)+fc(j)
    if ((ff+fw(j))<0.) fs=fc(j)
    if (fs>finf) fs=finf
    if (z<=1.e-02) fs=finf
    if (jf>0) then
      if(flag<0 .or. outp(1)) then
        p3d(i+(jf-1)*imax,j)=p(j)
        newdep3d(i+(jf-1)*imax)=newdep
        dh3d(i+(jf-1)*imax)=dh
      end if
      if(flag==-1) fs3d(i+(jf-1)*imax,j)=fs
      if(flag==-2) then
        fs3d(i+(jf-1)*imax,j)=fs
        ptran3d(i+(jf-1)*imax,j)=ptran(j)
        pzero3d(i,j)=pzero(j)
      end if
      if(flag==-3) then
        fs3d(i+(jf-1)*imax,j)=fs
        th3d(i+(jf-1)*imax,j)=thz(j)
      end if
      if(flag<=-4 .or. outp(1)) th3d(i+(jf-1)*imax,j)=thz(j)
    end if
    if (fs<fmn) then
      fmn=fs
      if (jf>0) then
        zfmin(i+(jf-1)*imax)=z
        pmin(i+(jf-1)*imax)=p(j)
      end if
    end if
    z=z+zinc
  end do Z_FS_loop
  if (jf>0) then
    fsmin(i+(jf-1)*imax)=fmn
    if(fmn==finf) then
      pmin(i+(jf-1)*imax)=p(nzs+1)
      zfmin(i+(jf-1)*imax)=zmax(i)
    end if
  end if
  return
end subroutine pstpi
