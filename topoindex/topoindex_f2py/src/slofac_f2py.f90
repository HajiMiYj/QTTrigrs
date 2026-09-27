! subroutine to identify cells downslope from each grid cell
! and compute weighting factors for partitioning runoff among the cells
!
! Rex L. Baum, USGS, 4 March 2002, latest revision 13 Mar 2013
!
! Refactored for f2py / in-process use:
!   * the output file units (u for dscfil, u2 for wffil) are opened directly
!     from the dscfil/wffil character arguments;
!   * the unused ordr argument is dropped;
!   * the log unit is replaced by an accumulated logmsg string;
!   * the hard `read*` / `stop` open-error handler is replaced by istatus != 0;
!   * `write(*,*)` error spam is removed.
! The weighting-factor computation is otherwise verbatim, including the
! three-decimal rounding via format 1020 (f6.3) and the ridge-crest rule.
subroutine slofac(z, celsiz, nodat, nodata, cel, dscfil, pwr, next, &
                  wffil, dir, spars, nrow, ncol, rc, dsctr, ridge, &
                  logmsg, istatus)
    !f2py threadsafe
    implicit none
    integer, intent(in) :: nodata, spars, nrow, ncol, rc
    double precision, intent(in) :: celsiz, nodat
    real, intent(in) :: z(ncol, nrow), pwr
    integer, intent(in) :: cel(ncol, nrow), dir(ncol, nrow), next(rc)
    character(len=*), intent(in) :: dscfil, wffil
    integer, intent(out) :: ridge(rc), dsctr, istatus
    character(len=4000), intent(out) :: logmsg

    integer :: k0, k, m0, m, i, j, l, u, u2, count
    integer :: num(9), ctr
    integer :: lh(9), rh(9), ll, lr, lmax
    real :: steep, dzdx1, dxdx1, dydx1, dzdx2, dxdx2, dydx2
    real :: r, bs, as, dipdir, nodats, test
    real :: pi, pio4
    double precision :: diag, slope(9)
    double precision :: sum1, sum2, w(9), a, b
    character(len=255) :: outfil
    character(len=6) :: scratch
    data lh / 4, 1, 2, 7, 5, 3, 8, 9, 6 /
    data rh / 2, 3, 6, 1, 5, 9, 4, 7, 8 /

    diag = celsiz * dsqrt(2.D0)
    pi = 3.1415926535
    pio4 = 45. * pi / 180.
    nodats = real(nodat)
    ! in general, dxdx1=cos(az_x1); dydx1=sin(az_x1); dxdx2=cos(az_x2); dydx2=sin(az_x2)
    ! for square grids they simplify to:
    dxdx1 = 1.
    dydx1 = 0.
    dxdx2 = sqrt(2.) / 2.
    dydx2 = sqrt(2.) / 2.
    r = dxdx2 / dxdx1
    logmsg = ''
    istatus = 0

    ! open output files
    outfil = dscfil
    outfil = adjustl(outfil)
    open (newunit=u, file=trim(outfil), err=300)
    outfil = wffil
    outfil = adjustl(outfil)
    open (newunit=u2, file=trim(outfil), err=300)

    ! search all cells for slope direction
    dsctr = 0
    do i = 1, nrow
        do j = 1, ncol
            test = abs(z(j, i) - nodats)
            if (test >= 0.1) then
                write (u, *) nodata
                write (u, *) cel(j, i)
                write (u2, *) nodata
                write (u2, *) cel(j, i)
                count = 0
                do k0 = 1, 3
                    do m0 = 1, 3
                        ! start at upper left corner and go around the cell
                        ! left to right and top to bottom
                        k = k0 - 2
                        m = m0 - 2
                        count = count + 1
                        ! set slopes equal to 0 before computing to aid sorting
                        slope(count) = 0.D0
                        num(count) = 0
                        if (k + i >= 1 .and. k + i <= nrow) then
                            if (m + j >= 1 .and. m + j <= ncol) then
                                ! if adjacent cell is a nodata cell, set slope
                                ! to a positive value
                                test = abs(z(j + m, i + k) - nodats)
                                if (test < 0.1) then
                                    slope(count) = 10.D0
                                    go to 40
                                end if
                                num(count) = cel(j + m, i + k)
                                if (k == 0 .or. m == 0) then
                                    ! compute slopes so that downslope is negative
                                    slope(count) = (z(j + m, i + k) - z(j, i)) / celsiz
                                else
                                    slope(count) = (z(j + m, i + k) - z(j, i)) / diag
                                end if
                            end if
                        end if
40                      continue
                    end do
                end do
                ! compute weighting factors
                ! case 0: pwr out of range -> default (D8 steepest path)
                if (pwr > 20.0) then
                    write (u, *) next(cel(j, i))
                    write (u2, 1020) 1.0
                    dsctr = dsctr + 1
                    go to 200
                end if

                ! case 1: uniform distribution among downslope cells
                if (pwr == 0.) then
                    sum1 = 0.
                    do l = 1, 9
                        w(l) = 0.
                        if (slope(l) < 0) w(l) = 1.
                        sum1 = sum1 + w(l)
                    end do
                    go to 170
                end if

                ! case 2: distribution proportional to slope
                if (pwr == 1.) then
                    sum1 = 0.
                    do l = 1, 9
                        w(l) = 0.
                        if (slope(l) < 0) w(l) = slope(l)
                        sum1 = sum1 + w(l)
                    end do
                    go to 170
                end if

                ! case 3: power-law distribution for slope
                if (pwr > 0.0 .and. pwr <= 20.0) then
                    sum1 = 0.
                    do l = 1, 9
                        w(l) = 0.D0
                        if (slope(l) < 0) then
                            a = abs(slope(l))
                            w(l) = a ** pwr
                        end if
                        sum1 = sum1 + w(l)
                    end do
                    go to 170
                end if

                ! case 4: Tarboton D-infinity variation (square grids only)
                if (pwr < 0.0) then
                    sum1 = 0.
                    steep = 0.
                    do l = 1, 9
                        w(l) = 0.D0
                    end do
                    lmax = dir(j, i)
                    steep = slope(lmax)
                    ! flat areas
                    if (steep >= 0) then
                        write (u, *) next(cel(j, i))
                        write (u2, 1020) 1.0
                        dsctr = dsctr + 1
                        go to 200
                    end if
                    ! sloping areas
                    lr = rh(lmax)
                    ll = lh(lmax)
                    a = slope(ll)
                    b = slope(lr)
                    if (a == b) then
                        write (u, *) next(cel(j, i))
                        write (u2, 1020) 1.0
                        dsctr = dsctr + 1
                        go to 200
                    end if
                    if (a < 0. .and. b < 0.) then
                        if (a > b) then
                            dzdx1 = slope(lmax)
                            dzdx2 = b
                            bs = (dzdx2 - r * dzdx1) / dydx2
                            as = (dzdx2 - bs * dydx2) / dxdx2
                            dipdir = atan(bs / as)
                            ! route indeterminate cases down steepest path
                            if (dipdir < 0. .or. dipdir > pio4) then
                                write (u, *) next(cel(j, i))
                                write (u2, 1020) 1.0
                                dsctr = dsctr + 1
                                go to 200
                            else
                                w(lmax) = pio4 - dipdir
                                w(lr) = dipdir
                                sum1 = pio4
                                if (w(lr) > w(lmax)) then
                                    w(lmax) = dipdir
                                    w(lr) = pio4 - dipdir
                                end if
                                go to 170
                            end if
                        else
                            dzdx1 = slope(lmax)
                            dzdx2 = a
                            bs = (dzdx2 - r * dzdx1) / dydx2
                            as = (dzdx2 - bs * dydx2) / dxdx2
                            dipdir = atan(bs / as)
                            if (dipdir < 0. .or. dipdir > pio4) then
                                write (u, *) next(cel(j, i))
                                write (u2, 1020) 1.0
                                dsctr = dsctr + 1
                                go to 200
                            else
                                w(lmax) = pio4 - dipdir
                                w(ll) = dipdir
                                sum1 = pio4
                                if (w(ll) > w(lmax)) then
                                    w(lmax) = dipdir
                                    w(ll) = pio4 - dipdir
                                end if
                                sum1 = pio4
                                go to 170
                            end if
                        end if
                    end if
                    ! a>0 and b>0
                    write (u, *) next(cel(j, i))
                    write (u2, 1020) 1.0
                    dsctr = dsctr + 1
                    go to 200
                end if
170             continue
                ! attempt to find ridge crests
                if (sum1 >= spars) ridge(cel(j, i)) = 1
                ! round weighting factors to three decimal places
                ! and fix total to equal 1
                ctr = 0
                sum2 = 0.
                do l = 1, 9
                    w(l) = w(l) / sum1
                    if (w(l) < 0.001) w(l) = 0.
                    if (w(l) > 0.) then
                        ctr = ctr + 1
                        write (scratch, 1020) w(l)
                        read (scratch, *) w(l)
                    end if
                    sum2 = sum2 + w(l)
                end do
                do l = 1, 9
                    if (num(l) == next(cel(j, i))) then
                        w(l) = w(l) + (1 - sum2)
                    end if
                end do
                ! if steepest slope is zero, divert flow to the next
                ! slope in the steepest downslope path
                if (ctr == 0) then
                    write (u, *) next(cel(j, i))
                    write (u2, 1020) 1.0
                    dsctr = dsctr + 1
                    go to 200
                end if
                do l = 1, 9
                    if (w(l) > 0) then
                        write (u, *) num(l)
                        write (u2, 1020) w(l)
                        dsctr = dsctr + 1
                    end if
                end do
200             continue
            end if
        end do
    end do
    close (u)
    close (u2)
    logmsg = 'Subroutine slofac completed normally'
    return

    ! error reporting
300 continue
    istatus = 1
    logmsg = '*** Error opening output file ***'
    return

1020 format (f6.3)
end subroutine slofac
