# Copyright 2011,2012,2016 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.

########################################################################
# Setup library
########################################################################
include(GrPlatform) #define LIB_SUFFIX

include_directories(${Boost_INCLUDE_DIR}
                    ${ZEROMQ_INCLUDE_DIRS})
link_directories(${Boost_LIBRARY_DIRS}
                 ${ZEROMQ_LIBRARIES})
list(APPEND envsim_sources
    iq_packet.cc
    envsim_source_impl.cc
    socket_meta_pdu_impl.cc
    stream_pdu_base.cc
    env_sink_impl.cc
    env_block_impl.cc
    env_source_impl.cc
    tx_time_tagger_impl.cc
    zmq_envsim_source_impl.cc )

set(envsim_sources "${envsim_sources}" PARENT_SCOPE)
if(NOT envsim_sources)
	MESSAGE(STATUS "No C++ sources... skipping lib/")
	return()
endif(NOT envsim_sources)

add_library(gnuradio-envsim SHARED ${envsim_sources})
target_link_libraries(gnuradio-envsim ${Boost_LIBRARIES} ${ZEROMQ_LIBRARIES} ${GNURADIO_ALL_LIBRARIES})
set_target_properties(gnuradio-envsim PROPERTIES DEFINE_SYMBOL "gnuradio_envsim_EXPORTS")

if(APPLE)
    set_target_properties(gnuradio-envsim PROPERTIES
        INSTALL_NAME_DIR "${CMAKE_INSTALL_PREFIX}/lib"
    )
endif(APPLE)

########################################################################
# Install built library files
########################################################################
include(GrMiscUtils)
GR_LIBRARY_FOO(gnuradio-envsim RUNTIME_COMPONENT "envsim_runtime" DEVEL_COMPONENT "envsim_devel")

########################################################################
# Build and register unit test
########################################################################
include(GrTest)

include_directories(${CPPUNIT_INCLUDE_DIRS})

list(APPEND test_envsim_sources
    ${CMAKE_CURRENT_SOURCE_DIR}/test_envsim.cc
    ${CMAKE_CURRENT_SOURCE_DIR}/qa_envsim.cc
)

add_executable(test-envsim ${test_envsim_sources})

target_link_libraries(
  test-envsim
  ${GNURADIO_RUNTIME_LIBRARIES}
  ${Boost_LIBRARIES}
  ${CPPUNIT_LIBRARIES}
  gnuradio-envsim
)

GR_ADD_TEST(test_envsim test-envsim)

########################################################################
# Print summary
########################################################################
message(STATUS "Using install prefix: ${CMAKE_INSTALL_PREFIX}")
message(STATUS "Building for version: ${VERSION} / ${LIBVER}")

