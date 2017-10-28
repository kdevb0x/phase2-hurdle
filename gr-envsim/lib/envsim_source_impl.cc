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

/* The code in this module is largely inspired by concepts from
 * https://github.com/osh/gr-eventstream
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gnuradio/io_signature.h>
#include "envsim_source_impl.h"

namespace gr {
namespace envsim {

envsim_source::sptr envsim_source::make(double sample_rate,
                                        int start_time_int_s,
                                        double start_time_frac_s) {
  return gnuradio::get_initial_sptr(
      new envsim_source_impl(sample_rate, start_time_int_s, start_time_frac_s));
}

/*
 * The private constructor
 */
envsim_source_impl::envsim_source_impl(double sample_rate, int start_time_int_s,
                                       double start_time_frac_s)
    : gr::sync_block("envsim_source", gr::io_signature::make(0, 0, 0),
                     gr::io_signature::make(1, 1, sizeof(gr_complex))),
      d_start_time_s(start_time_int_s),
      d_start_time_ps(start_time_frac_s),
      d_sample_rate(sample_rate),
      d_packet_counter(0) {
  // grow the residue capacity (not length) to our best guess at a maximum
  // packet size
  d_residue.reserve(DEFAULT_RESIDUE_SIZE);

  message_port_register_in(PACKET_PORT_ID);
  set_msg_handler(PACKET_PORT_ID,
                  boost::bind(&envsim_source_impl::packet_handler, this, _1));

  if (d_start_time_s != 0 || d_start_time_ps != 0) {
    d_time_initialized = true;
  } else {
    d_time_initialized = false;
  }
}

/*
 * Our virtual destructor.
 */
envsim_source_impl::~envsim_source_impl() {}

void envsim_source_impl::packet_handler(pmt::pmt_t pkt) {
  // skip adjusting for clock time for now and do initial testing in terms of
  // samples since the start of the flowgraph

  // std::cout << "running packet handler" << std::endl;

  // check for missing packets
  int this_packet_counter = packet_counter(pkt);
  if (d_packet_counter != this_packet_counter) {
    d_logger->warn("expected packet count %i, received %i", d_packet_counter,
                   this_packet_counter);
  }
  // update packet counter to the expected count for the next packet
  d_packet_counter = this_packet_counter + 1;

  // assume packets come in with metadata including the timestamp in
  // seconds, ps
  // add the timestamp_counts field
  add_counts_timestamp(pkt);

  // start working with the packet queue so grab the associated lock
  std::lock_guard<std::mutex> guard(d_packet_queue_mutex);

  // get the start time of this packet, in counts
  uint64_t pkt_start_counts = packet_timestamp_counts(pkt);

  // check if there are any packets currently in the queue
  if (d_packet_queue.size() > 0) {
    // get the start time of the last packet in the queue, in counts
    uint64_t last_start_counts = packet_timestamp_counts(d_packet_queue.back());

    // get the end time of the last packet in the queue, in counts
    uint64_t last_end_counts =
        last_start_counts + packet_length(d_packet_queue.back());

    // if this packet starts before the end of the last packet, drop it
    if (pkt_start_counts < last_end_counts) {
      d_logger->warn("packet dropped: overlaps existing packet");
      return;
    }
  }

  // if we're here, we need to add the packet to the queue
  d_packet_queue.push(pkt);

  // std::cout << "added event with timestamp " << pkt_start_counts <<
  // std::endl;

  // std::cout << "added packet to queue, queue size now: " <<
  // d_packet_queue.size() << std::endl;
  return;
}

// TODO: Extract IQ packet specific methods into the IQ Packet class

/*
 * Given an IQ packet as a PMT, try to extract the packet timestamp
 * ( not a required field, added by this block) from the packet metadata
 */
uint64_t envsim_source_impl::packet_timestamp_counts(pmt::pmt_t iq_packet) {
  pmt::pmt_t pmt_counts =
      pmt::dict_ref(pmt::car(iq_packet), TIMESTAMP_COUNTS, pmt::PMT_NIL);
  return pmt::to_uint64(pmt_counts);
}

/*
 * Given an IQ packet as a PMT, try to extract the packet length
 * from the packet metadata
 */
int envsim_source_impl::packet_length(pmt::pmt_t iq_packet) {
  pmt::pmt_t pmt_len =
      pmt::dict_ref(pmt::car(iq_packet), PACKET_LEN, pmt::PMT_NIL);
  return pmt::to_long(pmt_len);
}

/*
 * Given an IQ packet as a PMT, try to extract the packet count
 * from the packet metadata
 */
int envsim_source_impl::packet_counter(pmt::pmt_t iq_packet) {
  pmt::pmt_t pmt_counter =
      pmt::dict_ref(pmt::car(iq_packet), PACKET_COUNT, pmt::PMT_NIL);
  return pmt::to_long(pmt_counter);
}

/*
 * Given an IQ packet as a PMT, compute its timestamp in counts relative
 * to the start of the flowgraph
 */
void envsim_source_impl::add_counts_timestamp(pmt::pmt_t pkt) {
  // get the timestamp tuple from the packet metadata
  pmt::pmt_t meta = pmt::car(pkt);
  pmt::pmt_t timestamp_tuple =
      pmt::dict_ref(meta, PACKET_TIMESTAMP_S, pmt::PMT_NIL);

  int64_t pkt_s = pmt::to_uint64(pmt::tuple_ref(timestamp_tuple, 0));
  int64_t pkt_ps = pmt::to_uint64(pmt::tuple_ref(timestamp_tuple, 1));

  // this assumes timestamps will never be more than rougly 15 weeks apart
  int64_t delta_ps = (pkt_s - d_start_time_s) * 1e12 + pkt_ps - d_start_time_ps;

  // std::cout << "time delta in ps was " << delta_ps << std::endl;

  int64_t timestamp_counts = delta_ps * d_sample_rate / 1e12;

  // std::cout << "packet timestamp in counts is now " << timestamp_counts
  //           << std::endl;

  // TODO: Test what happens when timestamp_counts goes negative
  meta =
      pmt::dict_add(meta, TIMESTAMP_COUNTS, pmt::from_uint64(timestamp_counts));

  // store result back to packet
  pmt::set_car(pkt, meta);
}

void envsim_source_impl::set_start_time(int64_t start_time_s,
                                        int64_t start_time_ps) {
  d_start_time_s = start_time_s;
  d_start_time_ps = start_time_ps;
  d_time_initialized = true;
}

pmt::pmt_t envsim_source_impl::start_time() {
  pmt::pmt_t result = pmt::make_tuple(pmt::from_uint64(d_start_time_s),
                                      pmt::from_uint64(d_start_time_ps));
  return result;
}

int envsim_source_impl::work(int noutput_items,
                             gr_vector_const_void_star &input_items,
                             gr_vector_void_star &output_items) {
  // first check if our time has been initialized
  if (!d_time_initialized) {
    // if not, get the current time and store it off
    struct timeval tv_now;
    gettimeofday(&tv_now, NULL);
    d_start_time_s = tv_now.tv_sec;
    d_start_time_ps = tv_now.tv_usec * 1000000;
    d_time_initialized = true;

    d_logger->debug("start time initialized to %i %f s", d_start_time_s,
                    d_start_time_ps / 1e12);
  }

  // std::cout << "work called with noutput_items: " << noutput_items <<
  // std::endl;
  // std::cout << "packet queue size at start of work is: " <<
  // d_packet_queue.size() << std::endl;
  // setup output buffer and zeroize all elements
  gr_complex *out = (gr_complex *)output_items[0];
  memset(out, 0x00, noutput_items * sizeof(gr_complex));

  // d_logger->debug("work called with %i output items", noutput_items);

  // get the current number of samples we've processed to date
  // and use that as our internal block time
  int64_t b_time = nitems_written(0);

  // keep track of our progress in the current output buffer
  int output_offset = 0;

  // track how many items to output for each output operation
  int nitems_to_output = 0;

  // std::cout << "d_residue size is : " << d_residue.size() << std::endl;

  // check if there is anything left in the residue container
  if (d_residue.size() > 0) {
    // we have some leftover data from the last call. Output it

    // how many items are we going to output?
    nitems_to_output = std::min(d_residue.size(), (size_t)noutput_items);

    // set up iterators to the start and end of the range of elements to copy
    std::vector<std::complex<float> >::iterator first = d_residue.begin();
    std::vector<std::complex<float> >::iterator last =
        d_residue.begin() + nitems_to_output;

    // copy elements to output buffer
    std::copy(first, last, out);

    // erase the copied elements
    d_residue.erase(first, last);

    // update output offset
    output_offset = nitems_to_output;
    // return nitems_to_output;
  }

  // setup time bounds for the current sample buffer
  unsigned long long max_time = b_time + noutput_items;
  unsigned long long min_time = b_time;

  // std::cout << "time bounds are max: " << max_time << " min: " << min_time <<
  // std::endl;

  // we're goint to start processing the packet queue, so grab a
  // mutex lock for it
  std::lock_guard<std::mutex> guard(d_packet_queue_mutex);

  // std::cout << "Is packet queue empty?: " <<  d_packet_queue.empty() <<
  // std::endl;
  // grab items from the event queue and output as appropriate
  while (!d_packet_queue.empty()) {
    // first check if the item starts after the end of the current buffer
    uint64_t p_time = packet_timestamp_counts(d_packet_queue.front());
    int p_length = packet_length(d_packet_queue.front());

    // std::cout << "packet start time is: " <<  p_time <<  std::endl;
    // std::cout << "block time is: " <<  b_time <<  std::endl;

    if (p_time >= max_time) {
      // this starts after the end of this buffer. Stop processing
      // new packets
      // std::cout << "packet starts after end of buffer, exiting" << std::endl;
      break;
    }

    // if the current packet starts before the end of this buffer, we
    // should remove it from the queue
    pmt::pmt_t pkt = d_packet_queue.front();
    d_packet_queue.pop();

    // now check if the packet starts in the past
    if (p_time < b_time + output_offset) {
      // if this packet starts in the past, drop it and continue
      // processing new packets
      d_logger->warn(
          "packet starts in the past, dropping. packet late by counts: %i",
          b_time + output_offset - p_time);
    }

    // if the event isn't in the future or the past, pass it to output

    // std::cout << "begin packet output" <<  std::endl;
    // find the relative offset of the packet's start time in
    // our output buffer
    output_offset = p_time - b_time;
    // d_logger->debug(
    //     "processing packet with packet start count of %i for output sample
    //     %i",
    //     p_time, nitems_written(0) + output_offset);
    // std::cout << "outputting packet with timestamp " << p_time <<
    // std::endl;
    // std::cout << "output_offset is " << output_offset << std::endl;

    // compute number of samples to output
    nitems_to_output = std::min(p_length, noutput_items - output_offset);

    // std::cout << "p_len: " << p_length << " output offset: " << output_offset
    // << " noutput_items: " << noutput_items << " outputting: " <<
    // nitems_to_output << " items" << std::endl;

    // get a pointer to the packet's data portion
    size_t pkt_data_buf_len;

    const std::complex<float> *pkt_data_buf =
        c32vector_elements(pmt::cdr(pkt), pkt_data_buf_len);

    // copy from the start of the data portion of pkt to the output buffer
    std::memcpy(&out[output_offset], pkt_data_buf,
                nitems_to_output * sizeof(gr_complex));

    // update the output offset
    output_offset += nitems_to_output;

    // if the whole packet didn't fit in the output buffer, store
    // off the part that didn't fit
    if (nitems_to_output < p_length) {
      // get a pointer to the first item that didn't fit in the output
      // buffer
      const std::complex<float> *first = &pkt_data_buf[nitems_to_output];

      // get a pointer past the end of the packet's data
      const std::complex<float> *last = &pkt_data_buf[pkt_data_buf_len];

      // copy elements into resiude
      d_residue.insert(d_residue.end(), first, last);

      // std::cout <<"residue size now " << d_residue.size() << std::endl;
    }
  }

  if (output_offset == 0) {
    int64_t block_start_s, block_start_ps, block_stop_s, block_stop_ps;

    block_start_ps = d_start_time_ps + (1e12 / d_sample_rate) * min_time;
    block_stop_ps = d_start_time_ps + (1e12 / d_sample_rate) * max_time;

    // add integer seconds to start time
    block_start_s = d_start_time_s + int64_t(block_start_ps / 1e12);
    block_stop_s = d_start_time_s + int64_t(block_stop_ps / 1e12);

    // remove the integer seconds from the picoseconds variables
    block_start_ps = block_start_ps - int64_t(block_start_ps / 1e12) * 1e12;
    block_stop_ps = block_stop_ps - int64_t(block_stop_ps / 1e12) * 1e12;

    // d_logger->warn(
    //     "no packets found for time %lld %f to time %lld %f. zero filling.",
    //     block_start_s, double(block_start_ps) / 1e12, block_stop_s,
    //     double(block_stop_ps) / 1e12);

    // std::cerr << "U";
  }

  // Tell runtime system how many output items we produced.
  return noutput_items;
}

} /* namespace envsim */
} /* namespace gr */
