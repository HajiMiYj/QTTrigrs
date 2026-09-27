! Refactored TopoIndex control routines, split out of the monolithic
! official `tpindx.f90` program so they can be called in-process from Python
! via f2py.  The raster IO (ssizgrd/srdgrd1/rdflodir/isvgrd/mpfldr) lives in
! Python (topo_rewrite); only the parsing / ordering / listing logic below is
! compiled here.
!
!   * topo_in_read      - parse tpx_in.txt (fixed heading/value line pairs)
!   * correct_order     - correct the elevation ordering against D8 neighbours
!   * write_index_list  - write the cell-number / index-number list
!
! All three are "threadsafe": they perform no Python callbacks, so the f2py
! wrapper may release the GIL around the call and let the UI thread breathe.

subroutine topo_in_read(init_file, title, heading, aif, pwr, itmax, op, &
                        lspars, suffix, folder, demfil, dirfil, logmsg, istatus)
    !f2py threadsafe
    implicit none
    character(len=*), intent(in) :: init_file
    character(len=255), intent(out) :: title, heading, demfil, dirfil
    integer, intent(out) :: aif, itmax, istatus
    real, intent(out) :: pwr
    logical, intent(out) :: op(6), lspars
    character(len=8), intent(out) :: suffix
    character(len=224), intent(out) :: folder
    character(len=4000), intent(out) :: logmsg

    integer :: u, patlen
    character(len=8) :: dt
    character(len=10) :: tm
    character(len=64) :: line
    character(len=255) :: tmp_heading

    istatus = 0
    logmsg = ''
    call date_and_time(dt, tm)

    open (newunit=u, file=trim(init_file), status='old', err=210)

    ! ---- header of the returned log (mirrors the official u(9) listing) ----
    logmsg = trim(logmsg) // char(10)
    logmsg = trim(logmsg) // 'Starting TopoIndex' // char(10)
    logmsg = trim(logmsg) // 'Version: 1.0.14, 11May2015' // char(10)
    write (line, '(a,a,a,a,a,a)') 'Date: ', dt(5:6), '/', dt(7:8), '/', dt(1:4)
    logmsg = trim(logmsg) // trim(line) // char(10)
    write (line, '(a,a,a,a,a,a)') 'Time: ', tm(1:2), ':', tm(3:4), ':', tm(5:6)
    logmsg = trim(logmsg) // trim(line) // char(10)
    logmsg = trim(logmsg) // char(10)
    logmsg = trim(logmsg) // '-- LISTING OF INITIALIZATION DATA --' // char(10)

    ! line 1-2: heading, title
    read (u, '(a)', err=230, end=235) tmp_heading
    tmp_heading = adjustl(tmp_heading)
    read (u, '(a)', err=230, end=235) title
    title = adjustl(title)
    logmsg = trim(logmsg) // trim(tmp_heading) // char(10)
    logmsg = trim(logmsg) // trim(title) // char(10)
    ! line 3-4: aif
    read (u, '(a)', err=230, end=235) tmp_heading
    tmp_heading = adjustl(tmp_heading)
    read (u, *, err=230, end=235) aif
    logmsg = trim(logmsg) // trim(tmp_heading) // char(10)
    write (line, *) aif
    logmsg = trim(logmsg) // trim(adjustl(line)) // char(10)
    ! line 5-6: pwr, itmax
    read (u, '(a)', err=230, end=235) tmp_heading
    tmp_heading = adjustl(tmp_heading)
    read (u, *, err=230, end=235) pwr, itmax
    logmsg = trim(logmsg) // trim(tmp_heading) // char(10)
    write (line, *) pwr, itmax
    logmsg = trim(logmsg) // trim(adjustl(line)) // char(10)
    ! line 7-8: demfil
    read (u, '(a)', err=230, end=235) tmp_heading
    tmp_heading = adjustl(tmp_heading)
    read (u, '(a)', err=230, end=235) demfil
    demfil = adjustl(demfil)
    logmsg = trim(logmsg) // trim(tmp_heading) // char(10)
    logmsg = trim(logmsg) // trim(demfil) // char(10)
    ! line 9-10: dirfil
    read (u, '(a)', err=230, end=235) tmp_heading
    tmp_heading = adjustl(tmp_heading)
    read (u, '(a)', err=230, end=235) dirfil
    dirfil = adjustl(dirfil)
    logmsg = trim(logmsg) // trim(tmp_heading) // char(10)
    logmsg = trim(logmsg) // trim(dirfil) // char(10)
    ! line 11-12: op(1)
    read (u, '(a)', err=230, end=235) tmp_heading
    tmp_heading = adjustl(tmp_heading)
    read (u, *, err=230, end=235) op(1)
    logmsg = trim(logmsg) // trim(tmp_heading) // char(10)
    write (line, *) op(1)
    logmsg = trim(logmsg) // trim(adjustl(line)) // char(10)
    ! line 13-14: op(2)
    read (u, '(a)', err=230, end=235) tmp_heading
    tmp_heading = adjustl(tmp_heading)
    read (u, *, err=230, end=235) op(2)
    logmsg = trim(logmsg) // trim(tmp_heading) // char(10)
    write (line, *) op(2)
    logmsg = trim(logmsg) // trim(adjustl(line)) // char(10)
    ! line 15-16: op(3)
    read (u, '(a)', err=230, end=235) tmp_heading
    tmp_heading = adjustl(tmp_heading)
    read (u, *, err=230, end=235) op(3)
    logmsg = trim(logmsg) // trim(tmp_heading) // char(10)
    write (line, *) op(3)
    logmsg = trim(logmsg) // trim(adjustl(line)) // char(10)
    ! line 17-18: op(4)
    read (u, '(a)', err=230, end=235) tmp_heading
    tmp_heading = adjustl(tmp_heading)
    read (u, *, err=230, end=235) op(4)
    logmsg = trim(logmsg) // trim(tmp_heading) // char(10)
    write (line, *) op(4)
    logmsg = trim(logmsg) // trim(adjustl(line)) // char(10)
    ! line 19-20: op(5)
    read (u, '(a)', err=230, end=235) tmp_heading
    tmp_heading = adjustl(tmp_heading)
    read (u, *, err=230, end=235) op(5)
    logmsg = trim(logmsg) // trim(tmp_heading) // char(10)
    write (line, *) op(5)
    logmsg = trim(logmsg) // trim(adjustl(line)) // char(10)
    ! line 21-22: op(6), lspars
    read (u, '(a)', err=230, end=235) tmp_heading
    tmp_heading = adjustl(tmp_heading)
    read (u, *, err=230, end=235) op(6), lspars
    logmsg = trim(logmsg) // trim(tmp_heading) // char(10)
    write (line, *) op(6)
    logmsg = trim(logmsg) // trim(adjustl(line)) // char(10)

    ! path to elevation grid and output files (derived from demfil)
    patlen = scan(demfil, '/\', .true.)
    folder = demfil(1:patlen)
    folder = adjustl(folder)
    logmsg = trim(logmsg) // 'Path to elevation grid and output files' // char(10)
    logmsg = trim(logmsg) // trim(folder) // char(10)

    ! line 23-24: heading (ID code), suffix
    read (u, '(a)', err=230, end=235) heading
    heading = adjustl(heading)
    read (u, '(a)', err=230, end=235) suffix
    suffix = adjustl(suffix)
    logmsg = trim(logmsg) // trim(heading) // char(10)
    logmsg = trim(logmsg) // trim(suffix) // char(10)

    logmsg = trim(logmsg) // '-- END OF INITIALIZATION DATA --' // char(10)
    logmsg = trim(logmsg) // char(10)
    logmsg = trim(logmsg) // trim(title) // char(10)
    logmsg = trim(logmsg) // char(10)
    logmsg = trim(logmsg) // char(10)
    close (u)
    return

210 continue
    istatus = 21
    logmsg = ''
    return
230 continue
    istatus = 30
    close (u)
    return
235 continue
    istatus = 35
    close (u)
    return
end subroutine topo_in_read


subroutine correct_order(itmax, indx, lkup, cels, clcnt, rndx, ordr, &
                         cctr, logmsg, istatus)
    !f2py threadsafe
    implicit none
    integer, intent(in) :: itmax, clcnt
    integer, intent(inout) :: indx(clcnt), lkup(clcnt)
    integer, intent(in) :: cels(clcnt)
    integer, intent(out) :: rndx(clcnt), ordr(clcnt), cctr, istatus
    character(len=4000), intent(out) :: logmsg

    integer :: i, itctr, a, b, t1, t2
    character(len=64) :: line

    logmsg = ''
    istatus = 0
    cctr = 0

    do itctr = 1, itmax
        cctr = 0
        do i = 1, clcnt
            a = lkup(indx(i))
            b = lkup(cels(indx(i)))
            if (b > a) then
                cctr = cctr + 1
                t1 = indx(a)
                t2 = indx(b)
                lkup(cels(indx(i))) = a
                lkup(indx(i)) = b
                indx(a) = t2
                indx(b) = t1
            end if
            rndx(i) = indx(clcnt + 1 - i)
            a = rndx(i)
            ordr(a) = i
        end do
        if (cctr == 0) exit
    end do

    if (cctr > 0) then
        write (line, '(i6)') itmax
        logmsg = 'Corrections did not converge after ' // trim(adjustl(line)) // ' iterations'
        istatus = 1
    end if
end subroutine correct_order


subroutine write_index_list(rndx, outfil, clcnt, istatus)
    !f2py threadsafe
    implicit none
    integer, intent(in) :: rndx(clcnt), clcnt
    character(len=*), intent(in) :: outfil
    integer, intent(out) :: istatus
    integer :: i, u

    open (newunit=u, file=trim(outfil), status='replace', err=100)
    do i = 1, clcnt
        write (u, *) i, rndx(i)
    end do
    close (u)
    istatus = 0
    return

100 continue
    istatus = 1
end subroutine write_index_list
