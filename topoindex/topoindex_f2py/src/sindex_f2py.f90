! Indexes a real array "ra" of length n.
! Uses heapsort algorithm, based on section 8.3 of Numerical Recipes.
! Outputs the array ndx such that ra(ndx(j)) is in ascending order for j=1..n.
! The input quantities n and ra are not changed.
!
! Refactored for f2py: the argument order is (ra, n, ndx) so that n can be
! optional (default = size(ra)).  This matches the official sindex.f logic
! verbatim, with the two input arguments swapped.
subroutine sindex(ra, n, ndx)
    !f2py threadsafe
    implicit none
    integer, intent(in) :: n
    real, intent(in) :: ra(n)
    integer, intent(out) :: ndx(n)
    integer :: j, l, ir, ndxt, i
    real :: q

    do j = 1, n
        ndx(j) = j
    end do
    l = n / 2 + 1
    ir = n
10  continue
    if (l > 1) then
        l = l - 1
        ndxt = ndx(l)
        q = ra(ndxt)
    else
        ndxt = ndx(ir)
        q = ra(ndxt)
        ndx(ir) = ndx(1)
        ir = ir - 1
        if (ir == 1) then
            ndx(1) = ndxt
            return
        end if
    end if
    i = l
    j = 2 * l
20  if (j <= ir) then
        if (j < ir) then
            if (ra(ndx(j)) < ra(ndx(j + 1))) j = j + 1
        end if
        if (q < ra(ndx(j))) then
            ndx(i) = ndx(j)
            i = j
            j = j + j
        else
            ndx(i) = ndxt
            go to 10
        end if
        go to 20
    end if
    ndx(i) = ndxt
    go to 10
end subroutine sindex
