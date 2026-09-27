subroutine rnoff(imx1)
  ! 径流演算（文件 IO 已在 Python 完成，这里只用模块数组）。
  use grids; use input_vars
  implicit none
  integer:: i,j,l,imx1,id,next
  real:: rnof,inflx
  if(ans) then
    do j=1,nper
      do i=1,imx1
        ri(i)=ri_all(i+(j-1)*imax)
        ir(i)=ks(zo(i))
        ro(i)=0.
      end do
      do i=1,imx1
        id=indx(i)
        next=nxt(id)
        inflx=ro(id)+ri(id)
        if(depth(id)==0.0 .and. rizero(id)<0.0) then
          ir(id)=0
          rik(id+(j-1)*imax)=0.
          rnof=inflx-rizero(id)
          ro(id)=rnof
          do l=dsctr(id), dsctr(id+1)-1
            if (dsc(l).eq.id) then
              ro(dsc(l))=ro(dsc(l))+rnof*(wf(l)-1.)
            else
              ro(dsc(l))=ro(dsc(l))+rnof*wf(l)
            end if
          end do
        else if (ks(zo(id)).lt.inflx) then
          rik(id+(j-1)*imax)=1.d0
          rnof=inflx-ks(zo(id))
          ro(id)=rnof
          do l=dsctr(id), dsctr(id+1)-1
            if (dsc(l).eq.id) then
              ro(dsc(l))=ro(dsc(l))+rnof*(wf(l)-1.)
            else
              ro(dsc(l))=ro(dsc(l))+rnof*wf(l)
            end if
          end do
        else
          ir(id)=inflx
          rik(id+(j-1)*imax)=inflx/ks(zo(id))
          rnof=0.
          ro(id)=rnof
          ro(next)=ro(next)+rnof
        end if
      end do
    end do
  else
    do j=1,nper
      do i=1,imx1
        ri(i)=ri_all(i+(j-1)*imax)
      end do
      do i=1,imx1
        if (ks(zo(i)).lt.ri(i)) then
          ir(i)=ks(zo(i))
          rik(i+(j-1)*imax)=1.d0
        else
          ir(i)=ri(i)
          rik(i+(j-1)*imax)=ri(i)/ks(zo(i))
        end if
      end do
    end do
  end if
  return
end subroutine rnoff
