! subroutine to identify subjacent cells for a DEM grid
! uses a grid of slope directions for input
!
! Rex L. Baum, USGS, 15 February 2002, 29 Sept. 2005 converted to Fortran 90
!
! Refactored for f2py / in-process use:
!   * the input list unit (u1) is replaced by (save_list, list_file);
!   * the log unit (u2) is replaced by an accumulated logmsg string;
!   * the hard `read*` / `stop` on mismatch is replaced by istatus != 0;
!   * `write(*,*)` progress spam is removed (logs are centralised upstream);
!   * cell() is intent(in): the Python side (srdgrd1) already numbers the
!     valid cells 1..clcnt in row-major order, identically to the original
!     fill loop, so the redundant re-fill is dropped.
! The D8 neighbor / grid-mismatch logic is otherwise verbatim.
subroutine nxtcel(rc, prm, nodat, nodata, z, dir, cell, save_list, &
                  list_file, nrow, ncol, cels, mmcnt, logmsg, istatus)
    !f2py threadsafe
    implicit none
    integer, intent(in) :: rc, prm, nodata, nrow, ncol
    double precision, intent(in) :: nodat
    real, intent(in) :: z(ncol, nrow)
    integer, intent(in) :: dir(ncol, nrow), cell(ncol, nrow)
    logical, intent(in) :: save_list
    character(len=*), intent(in) :: list_file
    integer, intent(out) :: cels(rc), mmcnt, istatus
    character(len=4000), intent(out) :: logmsg

    integer :: i, j, kount, inew, jnew, a, b, k, u1
    integer :: m(9), n(9), list(prm)
    real :: nodats, test
    character(len=120) :: line
    data m / -1, -1, -1, 0, 0, 0, 1, 1, 1 /
    data n / -1, 0, 1, -1, 0, 1, -1, 0, 1 /

    kount = 0
    mmcnt = 0
    nodats = real(nodat)
    logmsg = ''
    istatus = 0
    cels = 0
    list = 0

    ! Open the optional D8 downslope-neighbour list file.
    if (save_list) then
        open (newunit=u1, file=trim(list_file), status='replace', err=100)
    end if

    do i = 1, nrow
        do j = 1, ncol
            test = abs(z(j, i) - nodats)
            if (test >= 0.1) then
                kount = kount + 1
                ! cell(j,i) is already numbered by the Python srdgrd1 stage;
                ! keep a local count only for parity with the original logic.
            end if
        end do
    end do

    logmsg = trim(logmsg) // '         Listing of grid mismatches' // char(10)
    logmsg = trim(logmsg) // 'Mismatch counter, Row, Column, Direction code' // char(10)

    row_traverse: do i = 1, nrow
        column_traverse: do j = 1, ncol
            test = abs(z(j, i) - nodats)
            if (test < 0.1) cycle column_traverse
            kount = 0
            inew = i
            jnew = j
            nextcell: do
                if (dir(jnew, inew) == nodata) then
                    mmcnt = mmcnt + 1
                    write (line, '(i8, 3(1x, i8))') mmcnt, jnew, inew, dir(jnew, inew)
                    logmsg = trim(logmsg) // trim(adjustl(line)) // char(10)
                    cycle column_traverse
                end if
                if (dir(jnew, inew) /= 5 .or. dir(jnew, inew) /= 0) then
                    if (inew >= 1 .and. inew <= nrow .and. &
                        jnew >= 1 .and. jnew <= ncol) then
                        kount = kount + 1
                        ! compute indices of next cell
                        a = inew + m(dir(jnew, inew))
                        b = jnew + n(dir(jnew, inew))
                        if (a == inew .and. b == jnew) then
                            exit nextcell
                        end if
                        if (a >= 1 .and. a <= nrow .and. b >= 1 .and. b <= ncol) then
                            list(kount) = cell(b, a)
                            if (list(kount) == 0) list(kount) = cell(jnew, inew)
                            test = abs(z(jnew, inew) - nodat)
                            if (test <= 0.1) exit nextcell
                            if (kount == 2) exit nextcell
                            cycle nextcell
                        else
                            exit nextcell
                        end if
                    end if
                end if
            end do nextcell
            if (save_list) write (u1, *) nodata
            if (save_list) write (u1, *) cell(j, i)
            if (kount > 1) then
                cels(cell(j, i)) = list(1)
                do k = 1, kount - 1
                    if (save_list) write (u1, *) list(k)
                end do
            else
                if (save_list) write (u1, *) cell(j, i)
                cels(cell(j, i)) = cell(j, i)
            end if
        end do column_traverse
    end do row_traverse

    if (save_list) close (u1)

    if (mmcnt > 0) then
        write (line, '(i12)') mmcnt
        logmsg = trim(logmsg) // trim(adjustl(line)) // ' mismatched cells' // char(10)
        logmsg = trim(logmsg) // 'Reconcile elevation grid and direction grid' // char(10)
        logmsg = trim(logmsg) // 'before attempting to use TopoIndex' // char(10)
        istatus = 1
        return
    end if

    write (line, '(i12, a)') mmcnt, ',  --,   --,  --'
    logmsg = trim(logmsg) // trim(adjustl(line)) // char(10)
    logmsg = trim(logmsg) // 'No grid mismatch found!' // char(10)
    logmsg = trim(logmsg) // 'Subroutine nxtcel completed normally' // char(10)
    return

100 continue
    istatus = 2
    logmsg = 'Error opening D8 downslope neighbour list file'
    return
end subroutine nxtcel
