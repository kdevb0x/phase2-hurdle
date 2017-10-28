/* -*- c++ -*- */
/*
 * Copyright 2017 <+YOU OR YOUR COMPANY+>.
 *
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */
#ifndef INCLUDED_ENVSIM_IQ_PACKET_H
#define INCLUDED_ENVSIM_IQ_PACKET_H

#include <pmt/pmt.h>
#include <complex>
#include <cstddef>
#include <string>
#include <uhd/types/time_spec.hpp>

namespace gr {
namespace envsim {

using namespace pmt;

// set up some constants for commonly used keys
const pmt_t PACKET_TIMESTAMP_S(pmt::mp("timestamp_s"));
const pmt_t PACKET_LEN(pmt::mp("packet_len"));
const pmt_t PACKET_COUNT(pmt::mp("packet_count"));

pmt_t iq_packet_create(std::string event_type, uhd::time_spec_t uhd_time,
                       int count);

pmt_t iq_packet_create(std::string event_type, uint64_t time_s,
                       uint64_t time_ps, int length, int count,
                       const std::complex<float> *data);

pmt_t iq_packet_create(std::string event_type, uhd::time_spec_t uhd_time,
                       int length, int count, const std::complex<float> *data);

}  // namespace envsim
}  // namespace gr

#endif /* INCLUDED_ENVSIM_IQ_PACKET_H */