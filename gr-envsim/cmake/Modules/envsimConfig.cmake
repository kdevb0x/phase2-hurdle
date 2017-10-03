INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_ENVSIM envsim)

FIND_PATH(
    ENVSIM_INCLUDE_DIRS
    NAMES envsim/api.h
    HINTS $ENV{ENVSIM_DIR}/include
        ${PC_ENVSIM_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    ENVSIM_LIBRARIES
    NAMES gnuradio-envsim
    HINTS $ENV{ENVSIM_DIR}/lib
        ${PC_ENVSIM_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
)

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(ENVSIM DEFAULT_MSG ENVSIM_LIBRARIES ENVSIM_INCLUDE_DIRS)
MARK_AS_ADVANCED(ENVSIM_LIBRARIES ENVSIM_INCLUDE_DIRS)

