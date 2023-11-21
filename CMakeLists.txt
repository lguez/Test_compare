cmake_minimum_required(VERSION 3.16)
project(Max_diff_rect LANGUAGES Fortran)
option(FETCH "Download Jumble")

if(FETCH)
  include(FetchContent)
  FetchContent_Declare(Jumble GIT_REPOSITORY
    https://github.com/lguez/Jumble.git)
  FetchContent_MakeAvailable(Jumble)
else()
  find_package(Jumble CONFIG REQUIRED)
endif()

add_executable(max_diff_rect max_diff_rect.f90)
target_link_libraries(max_diff_rect PRIVATE Jumble::jumble)
install(TARGETS max_diff_rect)
