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

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gnuradio/io_signature.h>
#include <math.h>
#include "zmq_envsim_source_impl.h"

namespace gr {
namespace envsim {

struct membuf : std::streambuf {
  membuf(void *b, size_t len) {
    char *bc = static_cast<char *>(b);
    this->setg(bc, bc, bc + len);
  }
};

zmq_envsim_source::sptr zmq_envsim_source::make(char *address, int timeout,
                                                int hwm, double sample_rate,
                                                int start_time_int_s,
                                                double start_time_frac_s) {
  return gnuradio::get_initial_sptr(new zmq_envsim_source_impl(
      address, timeout, hwm, sample_rate, start_time_int_s, start_time_frac_s));
}

/*
 * The private constructor
 */
zmq_envsim_source_impl::zmq_envsim_source_impl(char *address, int timeout,
                                               int hwm, double sample_rate,
                                               int start_time_int_s,
                                               double start_time_frac_s)
    : gr::sync_block("zmq_envsim_source", gr::io_signature::make(0, 0, 0),
                     gr::io_signature::make(1, 1, sizeof(gr_complex))),
      d_consumed_items(0),
      d_vsize(sizeof(gr_complex)),
      d_timeout(timeout),
      d_start_time_s(start_time_int_s),
      d_start_time_ps(start_time_frac_s),
      d_sample_rate(sample_rate),
      d_packet_counter(0),
      d_ontime_packet_counter(0),
      d_late_packet_counter(0) {
  /* "Fix" timeout value (ms for new API, us for old API) */
  int major, minor, patch;
  zmq::version(&major, &minor, &patch);

  if (major < 3) {
    d_timeout *= 1000;
  }

  /* Create context & socket */
  d_context = new zmq::context_t(1);
  d_socket = new zmq::socket_t(*d_context, ZMQ_PULL);

  /* Set high watermark */
  if (hwm >= 0) {
#ifdef ZMQ_RCVHWM
    d_socket->setsockopt(ZMQ_RCVHWM, &hwm, sizeof(hwm));
#else  // major < 3
    uint64_t tmp = hwm;
    d_socket->setsockopt(ZMQ_HWM, &tmp, sizeof(tmp));
#endif
  }
  /* Connect */
  d_socket->connect(address);

  if (d_start_time_s != 0 || d_start_time_ps != 0) {
    d_time_initialized = true;
  } else {
    d_time_initialized = false;
  }
}

/*
 * Our virtual destructor.
 */
zmq_envsim_source_impl::~zmq_envsim_source_impl() {
  d_socket->close();
  delete d_socket;
  delete d_context;
}

bool zmq_envsim_source_impl::has_pending() { return d_residue.size() > 0; }

int zmq_envsim_source_impl::flush_pending(gr_complex *out_buf,
                                          int noutput_items) {
  // how many items are we going to output?
  int nitems_to_output = std::min(d_residue.size(), (size_t)noutput_items);

  // set up iterators to the start and end of the range of elements to copy
  std::vector<std::complex<float> >::iterator first = d_residue.begin();
  std::vector<std::complex<float> >::iterator last =
      d_residue.begin() + nitems_to_output;

  // copy elements to output buffer
  std::copy(first, last, out_buf);

  // erase the copied elements
  d_residue.erase(first, last);

  return nitems_to_output;
}

bool zmq_envsim_source_impl::check_for_message() {
  /* Poll for input */
  bool wait = false;
  zmq::pollitem_t items[] = {
      {static_cast<void *>(*d_socket), 0, ZMQ_POLLIN, 0}};
  zmq::poll(&items[0], 1, wait ? d_timeout : 0);

  if (!(items[0].revents & ZMQ_POLLIN)) {
    return false;
  } else {
    return true;
  }
}

void zmq_envsim_source_impl::load_message() {
  /* Reset */
  d_msg.rebuild();
  d_consumed_items = 0;

  /* Get the message */
  d_socket->recv(&d_msg);

  membuf sb(d_msg.data(), d_msg.size());

  pmt::pmt_t pkt = pmt::deserialize(sb);

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

  // add the packet to the queue
  d_packet_queue.push(pkt);

  return;
}

// TODO: Extract IQ packet specific methods into the IQ Packet class

/*
 * Given an IQ packet as a PMT, try to extract the packet timestamp
 * ( not a required field, added by this block) from the packet metadata
 */
uint64_t zmq_envsim_source_impl::packet_timestamp_counts(pmt::pmt_t iq_packet) {
  pmt::pmt_t pmt_counts =
      pmt::dict_ref(pmt::car(iq_packet), TIMESTAMP_COUNTS, pmt::PMT_NIL);
  return pmt::to_uint64(pmt_counts);
}

/*
 * Given an IQ packet as a PMT, try to extract the packet length
 * from the packet metadata
 */
int zmq_envsim_source_impl::packet_length(pmt::pmt_t iq_packet) {
  pmt::pmt_t pmt_len =
      pmt::dict_ref(pmt::car(iq_packet), PACKET_LEN, pmt::PMT_NIL);
  return pmt::to_long(pmt_len);
}

/*
 * Given an IQ packet as a PMT, try to extract the packet count
 * from the packet metadata
 */
int zmq_envsim_source_impl::packet_counter(pmt::pmt_t iq_packet) {
  pmt::pmt_t pmt_counter =
      pmt::dict_ref(pmt::car(iq_packet), PACKET_COUNT, pmt::PMT_NIL);
  return pmt::to_long(pmt_counter);
}

/*
 * Given an IQ packet as a PMT, compute its timestamp in counts relative
 * to the start of the flowgraph
 */
void zmq_envsim_source_impl::add_counts_timestamp(pmt::pmt_t pkt) {
  // get the timestamp tuple from the packet metadata
  pmt::pmt_t meta = pmt::car(pkt);
  pmt::pmt_t timestamp_tuple =
      pmt::dict_ref(meta, PACKET_TIMESTAMP_S, pmt::PMT_NIL);

  int64_t pkt_s = pmt::to_uint64(pmt::tuple_ref(timestamp_tuple, 0));
  int64_t pkt_ps = pmt::to_uint64(pmt::tuple_ref(timestamp_tuple, 1));

  // this assumes timestamps will never be more than rougly 15 weeks apart
  int64_t delta_ps = (pkt_s - d_start_time_s) * 1e12 + pkt_ps - d_start_time_ps;

  // std::cout << "time delta in ps was " << delta_ps << std::endl;

  int64_t timestamp_counts = round(delta_ps / 1e12 * d_sample_rate);

  // std::cout << "packet timestamp in counts is now " << timestamp_counts
  //           << std::endl;

  // TODO: Test what happens when timestamp_counts goes negative
  meta =
      pmt::dict_add(meta, TIMESTAMP_COUNTS, pmt::from_uint64(timestamp_counts));

  // store result back to packet
  pmt::set_car(pkt, meta);
}

int zmq_envsim_source_impl::work(int noutput_items,
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

  // setup output buffer and zeroize all elements
  gr_complex *out = (gr_complex *)output_items[0];
  memset(out, 0x00, noutput_items * sizeof(gr_complex));

  // get the current number of samples we've processed to date
  // and use that as our internal block time
  int64_t b_time = nitems_written(0);

  // keep track of our progress in the current output buffer
  int output_offset = 0;

  // track how many items to output for each output operation
  int nitems_to_output = 0;

  if (has_pending()) {
    /* Flush anything pending */
    output_offset += flush_pending(out, noutput_items);
  }

  // setup time bounds for the current sample buffer
  unsigned long long max_time = b_time + noutput_items;
  unsigned long long min_time = b_time;

  // if not currently operating on a packet, check if there is a
  // new one ready. If so, load it in to the packet queue
  if (d_packet_queue.empty() & check_for_message()) {
    load_message();
  }

  // keep loading and processing messages until we either run out
  // of messages or run out of output space
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
      d_logger->warn("total num late packets: %i total num ontime packets: %i",
                     d_late_packet_counter, d_ontime_packet_counter);
      d_late_packet_counter += 1;
      // otherwise try to load the next message
      if (check_for_message()) {
        load_message();
      }
    } else {
      d_ontime_packet_counter += 1;
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

      // std::cout << "p_len: " << p_length << " output offset: " <<
      // output_offset
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
      // otherwise try to load the next message
      else if (check_for_message()) {
        load_message();
      }
    }
  }
  // Tell runtime system how many output items we produced.
  return noutput_items;
}

} /* namespace envsim */
} /* namespace gr */
