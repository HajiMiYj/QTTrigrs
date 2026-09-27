module trigrs_kernels
  use grids; use input_vars; use model_vars
  implicit none
  private
  public :: trigrs_solve
contains

subroutine compute_wtab()
  ! compute computed water-table elevations (wtab) from p3d/newdep3d/dh3d.
  ! Ports the water-table portion of official svijz(); list-file writing
  ! is handled in Python from the returned p3d/th3d arrays.
  integer:: i,jf,nw,wtctr,wctr
  integer:: wptr(nzs+1),wtptr(nzs+1)
  real:: wtab_temp
  real (dp):: delh,newdep,zns,zinc
  real (dp):: dwat,z,zbot,ztop,zwat(nzs+1),zwat0
  if(.not. outp(1)) return
  zns=float(nzs)
  do jf=1,nout
    do i=1,imax
      zbot=elev(i)-zmax(i)
      ztop=elev(i)-zmin
      zwat0=elev(i)-depth(i)
      zwat=zwat0
      wtctr=0; wctr=0; wptr=0; wtptr=0
      zinc=(zmax(i)-zmin)/zns
      delh=dh3d(i+(jf-1)*imax)
      newdep=newdep3d(i+(jf-1)*imax)
      p(1:nzs+1)=p3d(i+(jf-1)*imax,1:nzs+1)
      if(dcf>0. .and. (unsat(zo(i)) .or. igcap(zo(i)))) then
        if(rikzero(i)>=0.0) then
          dusz=depth(i)-1.d0/(alp(zo(i)))
          zwat(1)=elev(i)-(dusz-delh)
        else
          zwat(1)=elev(i)-newdep
        end if
        wtctr=1;wtptr(wtctr)=1;wptr(wtctr)=1
      else if (dcf<=0.) then
        call dzero_brac(nzs,p,wtctr,wtptr)
        wctr=0;dwat=0.d0;wptr=0
        do nw=1,nzs+1
          if(wtptr(nw)>0) then
            if(wtptr(nw)==2) then
              wctr=wctr+1
              z=zmin+zinc*float(nw-1)
              dwat=z
            end if
            if(wtptr(nw)==1) then
              wctr=wctr+1
              z=zmin+zinc*float(nw-1)
              dwat=z+zinc*(0.d0-p(nw))/(p(nw+1)-p(nw))
            end if
            if(rikzero(i)>=0.0) then
              zwat(nw)=elev(i)-dwat
              wptr(wctr)=nw
            else
              zwat(nw)=elev(i)-newdep
              wptr(wctr)=nw
            end if
          end if
          if(wctr==wtctr) exit
        end do
        if(p(nzs+1)<0.d0) then
          wtptr(nzs+1)=1
          wtctr=wtctr+1;wctr=wctr+1
          zwat(nzs+1)=elev(i)-depth(i)+beta*(p(nzs+1)-p0zmx)
          if(zwat(nzs+1)<(elev(i)-depth(i))) zwat(nzs+1)=elev(i)-depth(i)
          wptr(wtctr)=nzs+1
        end if
      end if
      if(wtctr==0)then
        if(p(1)>0. .and. zmin>=0.)then
          wtctr=wtctr+1;wctr=wctr+1
          wptr(wtctr)=1
          zwat(1)=elev(i);p(1)=0.
        end if
      end if
      select case (el_or_dep)
        case('eleva')
          wtab_temp = zwat(wptr(wtctr))
          if(wtab_temp < 0.) wtab_temp = elev(i)
          if (jf == 1) wtab_temp = elev(i) - depth(i)
          wtab(i+(jf-1)*imax)= wtab_temp
        case('depth')
          wtab_temp = elev(i)-zwat(wptr(wtctr))
          if(wtab_temp < 0.) wtab_temp = 0.
          if (jf == 1) wtab_temp = depth(i)
          wtab(i+(jf-1)*imax)= wtab_temp
        case default
          wtab_temp = zwat(wptr(wtctr))
          if(wtab_temp < 0.) wtab_temp = elev(i)
          if (jf == 1) wtab_temp = elev(i) - depth(i)
          wtab(i+(jf-1)*imax)= wtab_temp
      end select
    end do
  end do
  return
end subroutine compute_wtab


subroutine trigrs_solve( &
    ! ---- 尺寸与整型标量 ----
    imax_in, nwf_in, tx_in, nmax_in, flag_in, nper_in, spcg_in, nzs_in, &
    mmax_in, nzon_in, nout_in, kper_in, nts_in, &
    ! ---- 实型标量（单精度，对应 input_vars）----
    uww_in, zmin_in, t_in, dep_in, czmax_in, crizero_in, slomin_in, slomax_in, deepz_in, &
    ! ---- 时间步长（双精度，Python 侧按官方算法算好）----
    tinc_in, &
    ! ---- 字符串 ----
    flowdir_in, el_or_dep_in, deepwat_in, &
    ! ---- 逻辑标量 ----
    outp_in, rodoc_in, lskip_in, lany_in, llus_in, lps0_in, unsat0_in, bkgrof_in, lpge0_in, &
    ! ---- 分区/时间参数数组（假定形状）----
    ths_in, thr_in, alp_in, dif_in, c_in, phi_in, ks_in, uws_in, &
    capt_in, cri_in, tsav_in, &
    ! ---- 逻辑数组 ----
    unsat_in, igcap_in, &
    ! ---- 栅格数组 ----
    slo_in, zo_in, rizero_in, depth_in, zmax_in, elev_in, &
    ! ---- 径流数组 ----
    nxt_in, indx_in, dsctr_in, dsc_in, wf_in, ri_flat_in, ans_in, &
    ! ---- 输出（Python 预分配，假定形状）----
    fsmin_out, zfmin_out, pmin_out, wtab_out, rik1_out, &
    p3d_out, fs3d_out, th3d_out, ptran3d_out, pzero3d_out, dh3d_out, newdep3d_out, &
    nvu_out, nv_out, ro_out, ir_out, &
    ! ---- 输出标量 ----
    ncc_out, nccs_out)

  implicit none
  ! 输入标量
  integer, intent(in) :: imax_in, nwf_in, tx_in, nmax_in, flag_in, nper_in, spcg_in, nzs_in
  integer, intent(in) :: mmax_in, nzon_in, nout_in, kper_in, nts_in
  real, intent(in) :: uww_in, zmin_in, t_in, dep_in, czmax_in, crizero_in
  real, intent(in) :: slomin_in, slomax_in, deepz_in
  double precision, intent(in) :: tinc_in
  character(len=5), intent(in) :: flowdir_in, el_or_dep_in
  character(len=4), intent(in) :: deepwat_in
  logical, intent(in) :: outp_in(8), rodoc_in, lskip_in, lany_in, llus_in, lps0_in
  logical, intent(in) :: unsat0_in, bkgrof_in, lpge0_in
  ! 输入数组（假定形状）
  double precision, intent(in) :: ths_in(:), thr_in(:), alp_in(:), dif_in(:)
  double precision, intent(in) :: c_in(:), phi_in(:), ks_in(:), uws_in(:)
  double precision, intent(in) :: capt_in(:), cri_in(:), tsav_in(:)
  logical, intent(in) :: unsat_in(:), igcap_in(:)
  double precision, intent(in) :: slo_in(:), rizero_in(:), depth_in(:), zmax_in(:), elev_in(:)
  integer, intent(in) :: zo_in(:), nxt_in(:), indx_in(:), dsctr_in(:), dsc_in(:)
  double precision, intent(in) :: wf_in(:), ri_flat_in(:)
  logical, intent(in) :: ans_in
  ! 输出数组（假定形状）
  double precision, intent(inout) :: fsmin_out(:), zfmin_out(:), pmin_out(:)
  double precision, intent(inout) :: wtab_out(:), rik1_out(:)
  double precision, intent(inout) :: p3d_out(:,:), fs3d_out(:,:), th3d_out(:,:), ptran3d_out(:,:)
  double precision, intent(inout) :: pzero3d_out(:,:)
  double precision, intent(inout) :: dh3d_out(:), newdep3d_out(:)
  integer, intent(inout) :: nvu_out(:), nv_out(:)
  double precision, intent(inout) :: ro_out(:), ir_out(:)
  ! 输出标量
  integer, intent(out) :: ncc_out, nccs_out

  integer :: j, k, i, time_incr_ctr
  real :: outp_incr_min, outp_incr
  logical :: lwarn

  ! ---------------- 标量赋值 ----------------
  imax = imax_in
  nwf  = nwf_in
  tx   = tx_in
  nmax = nmax_in
  flag = flag_in
  nper = nper_in
  spcg = spcg_in
  nzs  = nzs_in
  mmax = mmax_in
  nzon = nzon_in
  nout = nout_in
  kper = kper_in
  nts  = nts_in

  uww = uww_in
  zmin = zmin_in
  t = t_in
  dep = dep_in
  czmax = czmax_in
  crizero = crizero_in
  slomin = slomin_in
  slomax = slomax_in
  deepz = deepz_in

  flowdir = flowdir_in
  el_or_dep = el_or_dep_in
  deepwat = deepwat_in

  outp = outp_in
  rodoc = rodoc_in
  lskip = lskip_in
  lany = lany_in
  llus = llus_in
  lps0 = lps0_in
  unsat0 = unsat0_in
  bkgrof = bkgrof_in
  lpge0 = lpge0_in

  pi = 3.141592653589793d0
  dg2rad = pi/180.0
  smt = 0.1d0
  lard = 12.d0
  eps = 1.0e-18
  tmin = 0.0
  tmax = dble(t)
  tns = dble(nts)
  tinc = tinc_in
  tis = tiny(1.0)

  ! ---------------- 分配 + 复制输入 ----------------
  allocate(indx(imax), nxt(imax))
  allocate(dsctr(imax+1), dsc(nwf), zo(imax))
  allocate(rikzero(imax), rik(imax*nper), ri(imax), ri_all(imax*nper), rizero(imax))
  allocate(ro(imax), wf(nwf), ir(imax))
  allocate(zmax(imax), slo(imax), depth(imax), elev(imax))
  allocate(unsat(nzon), igcap(nzon))
  allocate(ksav(nout+1))
  allocate(ths(nzon), thr(nzon), alp(nzon), dif(nzon), c(nzon), phi(nzon))
  allocate(ks(nzon), uws(nzon), capt(nper+1), cri(nper), tsav(nout))

  slo = real(slo_in, kind(slo))
  rizero = real(rizero_in, kind(rizero))
  depth = real(depth_in, kind(depth))
  zmax = real(zmax_in, kind(zmax))
  elev = real(elev_in, kind(elev))
  zo = int(zo_in)
  nxt = int(nxt_in)
  indx = int(indx_in)
  dsctr = int(dsctr_in)
  dsc = int(dsc_in)
  wf = real(wf_in, kind(wf))

  ths = real(ths_in, kind(ths))
  thr = real(thr_in, kind(thr))
  alp = real(alp_in, kind(alp))
  dif = real(dif_in, kind(dif))
  c = real(c_in, kind(c))
  phi = real(phi_in, kind(phi))
  ks = real(ks_in, kind(ks))
  uws = real(uws_in, kind(uws))
  capt = real(capt_in, kind(capt))
  cri = real(cri_in, kind(cri))
  tsav = real(tsav_in, kind(tsav))
  unsat = unsat_in
  igcap = igcap_in

  ! ---------------- 稳态入渗率 ----------------
  call steady(imax)

  ! ---------------- 径流演算 ----------------
  ri_all = real(ri_flat_in, kind(ri_all))
  ans = ans_in
  call rnoff(imax)

  ! ---------------- 结果数组 ----------------
  allocate(fsmin(imax*nout), pmin(imax*nout), zfmin(imax*nout))
  allocate(p(nzs+1), ptran(nzs+1), pzero(nzs+1), bline(nzs+1))
  allocate(fc(nzs+1), fw(nzs+1), thz(nzs+1), kz(nzs+1), trz(nzs+1))
  allocate(nvu(imax), nv(imax), uwsp(nzs+1), gs(nzon))
  allocate(chi(nzs+1))
  if(outp(1)) allocate(wtab(imax*nout))
  if(flag<0 .or. outp(1)) then
    allocate(p3d(imax*nout, nzs+1))
    allocate(dh3d(imax*nout), newdep3d(imax*nout))
    dh3d=0.d0; newdep3d=0.d0
    p3d=0.d0
  end if
  if(flag==-1) then
    allocate(fs3d(imax*nout, nzs+1))
    fs3d=0.d0
  end if
  if(flag==-2) then
    allocate(pzero3d(imax, nzs+1), ptran3d(imax*nout, nzs+1), fs3d(imax*nout, nzs+1))
    pzero3d=0.d0; ptran3d=0.d0; fs3d=0.d0
  end if
  if(flag==-3) then
    allocate(fs3d(imax*nout, nzs+1))
    fs3d=0.d0
    if(unsat0) then
      allocate(th3d(imax*nout, nzs+1))
      th3d=0.d0
    end if
  end if
  if(flag<=-4 .or. outp(1)) then
    if(flag/=-3) then
      if(.not. allocated(th3d)) allocate(th3d(imax*nout, nzs+1))
      th3d=0.d0
    end if
  end if
  fsmin=0.; zfmin=0.; pmin=0.
  if(outp(1)) wtab=0.
  p=0.; ptran=0.; pzero=0.; bline=0.; fc=0.; fw=0.
  nv=0; nvu=0

  ! ---------------- 时间步数组 ----------------
  allocate(tinc_sat(nts+1))
  tinc_sat=0.d0
  time_incr_ctr=0
  do k=1,kper
    do i=1,tx
      time_incr_ctr=time_incr_ctr+1
      if(t>=capt(k+1)) then
        tinc_sat(time_incr_ctr)=(capt(k+1)-capt(k))/float(tx)
      else
        tinc_sat(time_incr_ctr)=(t-capt(k))/float(tx)
      end if
    end do
  end do

  allocate(jsav(nts+1))
  jsav=0
  ksav=0
  lwarn=.false.
  do k=1,nout
    ts=tmin
    do j=1,nts
      if(unsat0) then
        if(tsav(k)>=ts .and. tsav(k)<ts+tinc) then
          if(tsav(k)/=ts) lwarn=.true.
          jsav(j)=k
          ksav(k)=j
          tsav(k)=ts
          exit
        else if(tsav(k)>=tmax) then
          jsav(nts+1)=k
          ksav(k)=nts+1
          tsav(k)=tmax
          exit
        end if
        ts=ts+tinc
      else
        if(tsav(k)>=ts .and. tsav(k)<ts+tinc_sat(j)) then
          if(tsav(k)/=ts) lwarn=.true.
          jsav(j)=k
          ksav(k)=j
          tsav(k)=ts
          exit
        else if(tsav(k)>=tmax) then
          jsav(nts+1)=k
          ksav(k)=nts+1
          tsav(k)=tmax
          exit
        end if
        ts=ts+tinc_sat(j)
      end if
    end do
  end do

  allocate(r(nmax), q(kper), qtime(2*nts+1), qb(nts+1), tcap(nts+2))
  allocate(qts(nts+1))
  if(outp(7)) allocate(rik1(imax*(nts+1)))
  if(.not. allocated(rik1)) allocate(rik1(1))
  nmax2=0
  nmin=1+nmax; nmn=1+mmax
  ncc_out=0; nccs_out=0
  r=0.; tcap=0.; qts=0.

  ! ---------------- 求解 ----------------
  if(unsat0) then
    do j=1,nzon
      gs(j)=((uws(j)/uww)-ths(j))/(1-ths(j))
    end do
    if(mmax<0) then
      mmax=20; nmn=1+mmax
      call unsinf(imax, ncc_out, nccs_out)
    else
      call unsfin(imax, ncc_out, nccs_out)
    end if
  else
    if(tx==1 .and. nout==1) then
      nccs_out=0
      if(mmax<0) then
        mmax=20; nmn=1+mmax
        call iverson(imax)
      else
        nmn=1+mmax
        call savage(imax, nccs_out)
      end if
    else
      if(mmax>0) then
        nmn=1+mmax
        call satfin(imax, nccs_out)
      else
        mmax=20; nmn=1+mmax
        call satinf(imax, nccs_out)
      end if
    end if
  end if

  ! ---------------- 水位面输出 ----------------
  if(outp(1)) call compute_wtab()

  ! ---------------- 复制结果到输出数组 ----------------
  fsmin_out = dble(fsmin)
  zfmin_out = dble(zfmin)
  pmin_out  = dble(pmin)
  wtab_out  = 0.d0
  if(allocated(wtab)) wtab_out = dble(wtab)
  rik1_out  = 0.d0
  if(allocated(rik1) .and. size(rik1)==imax*(nts+1)) rik1_out = dble(rik1)

  p3d_out = 0.d0
  if(allocated(p3d)) p3d_out = dble(p3d)
  fs3d_out = 0.d0
  if(allocated(fs3d)) fs3d_out = dble(fs3d)
  th3d_out = 0.d0
  if(allocated(th3d)) th3d_out = dble(th3d)
  ptran3d_out = 0.d0
  if(allocated(ptran3d)) ptran3d_out = dble(ptran3d)
  pzero3d_out = 0.d0
  if(allocated(pzero3d)) pzero3d_out = dble(pzero3d)
  dh3d_out = 0.d0
  if(allocated(dh3d)) dh3d_out = dble(dh3d)
  newdep3d_out = 0.d0
  if(allocated(newdep3d)) newdep3d_out = dble(newdep3d)

  nvu_out = int(nvu)
  nv_out = int(nv)
  ro_out = dble(ro)
  ir_out = dble(ir)

  ! ---------------- 释放模块数组 ----------------
  deallocate(indx, nxt, dsctr, dsc, zo, rikzero, rik, ri, ri_all, rizero)
  deallocate(ro, wf, ir, zmax, slo, depth, elev)
  deallocate(unsat, igcap, ksav, ths, thr, alp, dif, c, phi, ks, uws, capt, cri, tsav)
  deallocate(fsmin, pmin, zfmin, p, ptran, pzero, bline, fc, fw, thz, kz, trz)
  deallocate(nvu, nv, uwsp, gs, chi)
  if(allocated(wtab)) deallocate(wtab)
  if(allocated(p3d)) deallocate(p3d)
  if(allocated(dh3d)) deallocate(dh3d)
  if(allocated(newdep3d)) deallocate(newdep3d)
  if(allocated(fs3d)) deallocate(fs3d)
  if(allocated(th3d)) deallocate(th3d)
  if(allocated(ptran3d)) deallocate(ptran3d)
  if(allocated(pzero3d)) deallocate(pzero3d)
  if(allocated(rik1)) deallocate(rik1)
  deallocate(tinc_sat, jsav, r, q, qtime, qb, tcap, qts)

  return
end subroutine trigrs_solve

end module trigrs_kernels
