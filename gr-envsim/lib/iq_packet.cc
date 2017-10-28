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

#include "iq_packet.h"

/*
 * An IQ packet in this context is defined as a GNURADIO PDU,
 * which is another way to say that it is a PMT (polymorphic type)
 * pair. PMTs borrow some terminology from LISP, using car for the
 * first element of a sequence and cdr for the rest of the elements
 * of a sequence.
 * The first element or car in an IQ packet PMT is a PMT dictionary.
 * The second element or cdr of this pair is a comlex32 vector,
 * where each IQ sample is made up of two floats.
 *
 * The only required dictionary elements are "timestamp_s",
 * which is the timestamp of the start of the packet, "packet_count",
 * which is used to detect dropped packets, and
 * "packet_len", which is the number of samples in the packet.
 * This timestamp is stored as a PMT tuple. The first
 * element of the tuple is an integer timestamp of seconds
 * since 1970 aka epoch time.
 * The second element of this tuple is the fractional portion
 * of that timestamp, in nanoseconds, stored as a 64 bit int.
 */

namespace gr {
namespace envsim {

pmt_t iq_packet_create(std::string event_type, uhd::time_spec_t uhd_time,
                       int count) {
  // setup header metadata info
  pmt_t meta = make_dict();
  pmt_t timestamp = make_tuple(from_uint64(uhd_time.get_full_secs()),
                               from_uint64(uhd_time.get_frac_secs() * 1e12));
  meta = dict_add(meta, PACKET_TIMESTAMP_S, timestamp);
  meta = dict_add(meta, PACKET_LEN, from_long(0));
  meta = dict_add(meta, PACKET_COUNT, from_long(count));

  // store data to PMT
  std::complex<float> temp;
  pmt_t data = init_c32vector(0, &temp);

  return cons(meta, data);
}

pmt_t iq_packet_create(std::string event_type, uint64_t time_s,
                       uint64_t time_ps, int length, int count,
                       const std::complex<float> *samples) {
  // setup header metadata info
  pmt_t meta = make_dict();
  pmt_t timestamp = make_tuple(from_uint64(time_s), from_uint64(time_ps));
  meta = dict_add(meta, PACKET_TIMESTAMP_S, timestamp);
  meta = dict_add(meta, PACKET_LEN, from_long(length));
  meta = dict_add(meta, PACKET_COUNT, from_long(count));

  // store data to PMT
  pmt_t data = init_c32vector(length, samples);

  return cons(meta, data);
}

pmt_t iq_packet_create(std::string event_type, uhd::time_spec_t uhd_time,
                       int length, int count, const std::complex<float> *data) {
  // convert from uhd time_spec to int seconds and frac seconds
  return iq_packet_create(event_type, uhd_time.get_full_secs(),
                          uhd_time.get_frac_secs() * 1e12, length, count, data);
}

} /* namespace envsim */
} /* namespace gr */