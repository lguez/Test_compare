program max_diff_rect

  ! Author: Lionel GUEZ

  ! This is a Fortran 2003 program.

  ! The program takes two files as arguments. It makes a numerical
  ! comparison of "rectangular" regions of the two files. In each
  ! file, the region to be compared must contain values separated by
  ! commas and/or blanks. In each line of the region, the columns to
  ! be compared must contain numeric values. Values not compared may
  ! be not numerical.

  ! The program reads a namelist rectangle twice: once for each
  ! file. The default values for the second namelist are values out of
  ! the first namelist.

  use jumble, only: compare, csvread, get_command_arg_dyn, assert

  implicit none

  double precision, allocatable, dimension(:,:):: data_old, data_new
  character(len=2) choice
  integer i

  integer first_c ! first column to read
  integer last_c ! last column to read
  integer n_col ! number of columns to read

  integer first_r ! first row to read
  integer last_r ! last row to read
  integer n_rows ! number of rows to read

  character(len=20) tag
  character(len = :), allocatable:: filename1, filename2
  character(len = *), parameter:: USAGE="usage: max_diff_rect file file"
  logical, allocatable:: valid(:, :), valid_1d(:)

  namelist /rectangle/first_c, last_c, first_r, last_r

  !----------------------------------------------------------

  call get_command_arg_dyn(1, filename1, USAGE)
  call get_command_arg_dyn(2, filename2, USAGE)

  ! Default values:
  first_r = 1
  last_r = 0 ! meaning last in file
  first_c = 1
  last_c = 0 ! meaning last in file

  write(unit = *, nml = rectangle)
  print *, "Enter namelist rectangle for first file:"
  read(unit = *, nml = rectangle)
  call csvread(filename1, data_old, first_r, first_c, last_r, last_c)
  
  if (.not. allocated(data_old)) then
     print *, "max_diff_rect: could not read from " // filename1
     stop 1
  end if

  n_rows = size(data_old, 1)
  n_col = size(data_old, 2)

  ! Do not reset rectangle to 1, 0, 1, 0, default values are now
  ! values from the first file:
  print *, "Enter namelist rectangle for second file (default values are ", &
       "values chosen for the first file):"
  read(unit = *, nml = rectangle)

  ! If the user specifies the number of rows or columns in the
  ! namelist, it should correspond to what has already been read:
  if (last_r /= 0 .and. last_r - first_r + 1 /= n_rows) &
       stop 'Numbers of rows differ.'
  if (last_c /= 0 .and. last_c - first_c + 1 /= n_col) &
       stop 'Numbers of columns differ.'

  call csvread(filename2, data_new, first_r, first_c, last_r, last_c)

  if (.not. allocated(data_new)) then
     print *, "max_diff_rect: could not read from " // filename2
     stop 1
  end if
  
  call assert(shape(data_old) == shape(data_new), 'Shapes should be identical.')
  allocate(valid(size(data_old, 1), size(data_old, 2)), &
       valid_1d(size(data_old, 1)))
  valid = .true.
  valid_1d = .true.

  do
     print *
     print *, 'Compare:'
     print *, '- the whole matrix (w)'
     print *, '- all columns, column by column (c)'
     print *, '- a single column (column number)'
     print *, 'or exit (q).'
     choice = ''
     write(unit=*, fmt='(a)', advance='no') 'Your choice? '
     read *, choice
     select case (choice(:1))
     case ('w')
        call compare(data_old, data_new, tag = "Whole matrix", &
             comp_mag = .false., report_id = .true., quiet = .false., &
             valid = valid)
     case ('c')
        do i = 1, n_col
           write(unit=tag, fmt=*) "Column ", i
           call compare(data_old(:,i), data_new(:,i), trim(tag), &
                comp_mag=.false., report_id=.true., quiet=.false., &
                valid = valid_1d)
           print *
!!$           write(unit=*, fmt='(a)', advance='no') &
!!$                'Hit <return> for next column.'
!!$           read *
        end do
     case ('q')
        exit
     case default
        if (verify(choice, " 0123456789") /= 0) stop 'Incorrect answer.'
        ! A column number was entered
        read(unit=choice, fmt=*) i
        write(unit=tag, fmt=*) "Column ", i
        call compare(data_old(:,i), data_new(:,i), trim(tag), &
             comp_mag=.false., report_id=.true., quiet=.false., &
             valid = valid_1d)
     end select
  end do

end program max_diff_rect
