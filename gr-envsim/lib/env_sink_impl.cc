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

// TODO: Implement throttling in-block via some sort of flow control

// TODO: Implement the concept of a packet size similar to USRP over the wire
// packets

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gnuradio/io_signature.h>
#include <pmt/pmt.h>
#include <algorithm>
#include <map>
#include "env_sink_impl.h"

namespace gr {
namespace envsim {

env_sink::sptr env_sink::make(const std::string &event_name,
                              unsigned int max_block_size,
                              int64_t schedule_offset_ps, double sample_rate,
                              const std::string tx_pkt_len_name, char *address,
                              int timeout, int hwm) {
  return gnuradio::get_initial_sptr(
      new env_sink_impl(event_name, max_block_size, schedule_offset_ps,
                        sample_rate, tx_pkt_len_name, address, timeout, hwm));
}

/*
 * The private constructor
 */
env_sink_impl::env_sink_impl(const std::string &event_name,
                             unsigned int max_block_size,
                             int64_t schedule_offset_ps, double sample_rate,
                             const std::string tx_pkt_len_name, char *address,
                             int timeout, int hwm)
    : gr::block("env_sink", gr::io_signature::make(1, 1, sizeof(gr_complex)),
                gr::io_signature::make(0, 0, 0)),
      d_max_block_size(max_block_size),
      d_schedule_offset_ps(schedule_offset_ps),  // deprecated
      d_event_name(event_name),
      d_first_iteration(false),
      d_itemsize(sizeof(gr_complex)),
      d_remaining_samps_in_burst(0),
      d_sample_rate(sample_rate),
      d_packet_counter(0),
      d_tx_time_tag(pmt::mp(TX_TIME_NAME)),
      d_tx_pkt_len_tag(pmt::mp(tx_pkt_len_name)),
      d_tx_sob_tag(pmt::mp(TX_SOB_NAME)),
      d_tx_eob_tag(pmt::mp(TX_EOB_NAME)),
      d_vsize(sizeof(gr_complex)),
      d_timeout(timeout) {
  /* "Fix" timeout value (ms for new API, us for old API) */
  int major, minor, patch;
  zmq::version(&major, &minor, &patch);

  if (major < 3) {
    d_timeout *= 1000;
  }

  /* Create context & socket */
  d_context = new zmq::context_t(1);
  d_socket = new zmq::socket_t(*d_context, ZMQ_PUSH);

  /* Set high watermark */
  if (hwm >= 0) {
#ifdef ZMQ_SNDHWM
    d_socket->setsockopt(ZMQ_SNDHWM, &hwm, sizeof(hwm));
#else  // major < 3
    uint64_t tmp = hwm;
    d_socket->setsockopt(ZMQ_HWM, &tmp, sizeof(tmp));
#endif
  }
  /* Bind */
  d_socket->bind(address);

  // initialize this block's time
  struct timeval tv1;
  gettimeofday(&tv1, NULL);
  d_block_time = uhd::time_spec_t(tv1.tv_sec, double(tv1.tv_usec) / 1e6);

  d_logger->info("block time initialized to %i %f s",
                 d_block_time.get_full_secs(), d_block_time.get_frac_secs());

  // save off whether we're using packet length tags or assuming to use tx_sob
  // tags
  d_using_pkt_len_tags = (tx_pkt_len_name != "");
}

/*
 * Our virtual destructor.
 */
env_sink_impl::~env_sink_impl() {
  d_socket->close();
  delete d_socket;
  delete d_context;
}

void env_sink_impl::send_message(const void *in_buf, const int msg_len) {
  zmq::message_t msg(msg_len);
  memcpy(msg.data(), in_buf, msg_len);

  /* Send */
  d_socket->send(msg);

  return;
}

void env_sink_impl::process_output_packet(int n_samps_to_process,
                                          const gr_complex *in) {
  // now we know how many samples to process this call. Create the relevant
  // event

  d_logger->debug("processing %i samples", n_samps_to_process);
  uhd::time_spec_t pkt_time = d_block_time + d_schedule_offset_ps / 1e12;
  pmt::pmt_t iq_pkt = iq_packet_create(
      d_event_name, pkt_time, n_samps_to_process, d_packet_counter, &in[0]);

  // update our internal packet counter
  d_packet_counter += 1;

  // update the block time
  d_logger->debug("incrementing block time by %f seconds",
                  double(n_samps_to_process) / d_sample_rate);

  d_block_time += uhd::time_spec_t(double(n_samps_to_process) / d_sample_rate);

  d_logger->debug("block time now %i %f s", d_block_time.get_full_secs(),
                  d_block_time.get_frac_secs());

  // ensure the iq packet pmt doesn't get garbage collected before the next
  // iteration of this block
  d_event_list.push_back(iq_pkt);

  d_logger->debug("sending packet with start timestamp of %i %f",
                  pkt_time.get_full_secs(), pkt_time.get_frac_secs());

  // serialize and send packet
  std::stringbuf sb("");
  pmt::serialize(iq_pkt, sb);
  send_message(sb.str().c_str(), sb.str().length());
}

void env_sink_impl::forecast(int noutput_items,
                             gr_vector_int &ninput_items_required) {
  if (d_first_iteration) {
    ninput_items_required[0] = 0;
  } else {
    ninput_items_required[0] = noutput_items;
  }
}

int env_sink_impl::general_work(int noutput_items, gr_vector_int &ninput_items,
                                gr_vector_const_void_star &input_items,
                                gr_vector_void_star &output_items) {
  // get simpler pointer to input sample buffer
  const gr_complex *in = (const gr_complex *)input_items[0];

  d_logger->debug("work called with %i input items, %i output items",
                  ninput_items[0], noutput_items);

  d_logger->debug("block time at start of work call %i %f s",
                  d_block_time.get_full_secs(), d_block_time.get_frac_secs());

  // TODO: Do a pass on sanity checking tag values so we don't get weird
  // behavior, and warn people about bad values to help with debug

  int nitems_consumed = 0;
  int n_samps_to_process;
  // clear out event list (just in case)
  d_event_list.clear();

  // check if there are any remaining samples in the current burst
  if (d_remaining_samps_in_burst > 0) {
    d_logger->debug("We are mid-burst: samples remaining in burst: %ld",
                    d_remaining_samps_in_burst);

    // compute how many samples we should try to process this call
    n_samps_to_process = std::min(d_remaining_samps_in_burst, ninput_items[0]);

    // making sure block fits in max block size
    n_samps_to_process = std::min(n_samps_to_process, d_max_block_size);

    // get all tags in range and warn that they're being ignored
    std::vector<tag_t> tags_in;

    // get all tags in range for this block of samples
    get_tags_in_window(tags_in, 0, 0, n_samps_to_process);

    for (std::vector<tag_t>::iterator it = tags_in.begin(); it != tags_in.end();
         ++it) {
      d_logger->warn(
          "mid-burst: Ignoring tag at offset %ld with key %s and value %s",
          it->offset, pmt::write_string(it->key).c_str(),
          pmt::write_string(it->value).c_str());
    }

    // decrement n_samples in burst
    d_remaining_samps_in_burst -= n_samps_to_process;

    // generate and send iq packet
    process_output_packet(n_samps_to_process, in);

    // Tell runtime system how many output items we produced.
    consume_each(n_samps_to_process);
    return 0;
  }

  // otherwise we don't know whether or not that we're in the middle of a burst
  // Assume the answer is no

  // First check if we're using packet length tags
  if (d_using_pkt_len_tags) {
    d_logger->debug("using packet length tags");
    // We're using packet length tags so go search for them
    std::vector<tag_t> tx_pkt_len_tags;

    // find all packet len and tx time tags
    get_tags_in_window(tx_pkt_len_tags, 0, 0, ninput_items[0],
                       d_tx_pkt_len_tag);

    // if there are no tags found, default to outputting a block of samples
    // TODO: Come back and harmonize this with default UHD behavior of dropping
    // samples when packet length tags are not where they are expected to be
    if (tx_pkt_len_tags.size() == 0) {
      d_logger->warn("no packet length tags found");
      n_samps_to_process = ninput_items[0];

      // making sure block fits in max block size
      n_samps_to_process = std::min(n_samps_to_process, d_max_block_size);

      // generate and send iq packet
      d_logger->warn("no packet len tags found. outputting sample block");
      process_output_packet(n_samps_to_process, in);

      // Tell runtime system how many output items we produced.
      consume_each(n_samps_to_process);
      return 0;
    }
    d_logger->debug("found %i packet length tags", tx_pkt_len_tags.size());

    // if the first tx packet len tag occurs anywhere other than the first
    // sample of this block, output all samples up to the tag
    if (tx_pkt_len_tags[0].offset != nitems_read(0)) {
      n_samps_to_process = tx_pkt_len_tags[0].offset - nitems_read(0);

      // making sure block fits in max block size
      n_samps_to_process = std::min(n_samps_to_process, d_max_block_size);

      d_logger->debug(
          "first packet length tag at offset %ld, nitems_read is %ld. Trying "
          "to fast forward to tag",
          tx_pkt_len_tags[0].offset, nitems_read(0));

      // generate and send iq packet
      process_output_packet(n_samps_to_process, in);

      // Tell runtime system how many output items we produced.
      consume_each(n_samps_to_process);
      return 0;
    }

    // otherwise this tag is on the first sample of this block. Compute how
    // many samples to output, update the d_remaining_samps_in_burst, and look
    // for a tx time tag

    // TODO: Handle the case where we have buggy packet lengths resulting in
    // "overlapping" packets
    int pkt_len = pmt::to_long(tx_pkt_len_tags[0].value);

    n_samps_to_process = std::min(pkt_len, ninput_items[0]);

    // making sure block fits in max block size
    n_samps_to_process = std::min(n_samps_to_process, d_max_block_size);

    d_remaining_samps_in_burst = pkt_len - n_samps_to_process;
    d_logger->debug(
        "processing packet len tag: pkt len: %i  samps to process: %i samps "
        "remaining in burst: %i",
        pkt_len, n_samps_to_process, d_remaining_samps_in_burst);

    std::vector<tag_t> tx_time_tags;
    get_tags_in_window(tx_time_tags, 0, 0, noutput_items, d_tx_time_tag);

    // check for existance of a time tag and that the first tx time tag offset
    // is on the first sample of this block. If so, extract the tag value and
    // update the current timestamp

    if ((tx_time_tags.size() > 0) &&
        (tx_time_tags[0].offset == nitems_read(0))) {
      uint64_t int_seconds =
          pmt::to_uint64(pmt::tuple_ref(tx_time_tags[0].value, 0));
      double frac_seconds =
          pmt::to_double(pmt::tuple_ref(tx_time_tags[0].value, 1));

      d_logger->debug("tag found with timestamp: %i %f s", int_seconds,
                      frac_seconds);
      uhd::time_spec_t new_time(int_seconds, frac_seconds);

      // adding 0.1 of a sample to the test to account for meaninless precision
      // errors
      if (new_time + 0.1 / d_sample_rate >= d_block_time) {
        d_logger->debug("updating block time to match tag: %i %f s",
                        int_seconds, frac_seconds);

      } else {
        d_logger->warn(
            "tagged stream mode: block time of %i %f is ahead of "
            "tag time: %i "
            "%f s, this may indicate a math error in tx_time tag inputs, "
            "updating block time",
            d_block_time.get_full_secs(), d_block_time.get_frac_secs(),
            int_seconds, frac_seconds);
      }
      d_block_time = new_time;
    }
    // TODO: Warn that we're ignoring this TX time tag if the offset doesn't
    // match up

    // otherwise the default behavior won't modify the current internal time of
    // this block

    // generate and send iq packet
    d_logger->debug("outputting packet with packet length tags");
    process_output_packet(n_samps_to_process, in);

    // Tell runtime system how many output items we produced.
    consume_each(n_samps_to_process);
    return 0;
  } else {
    // If we get here, assume we're using SOB and EOB tags

    d_logger->debug("using TX SOB tags");
    std::vector<tag_t> tx_sob_tags;

    // find all tx sob tags
    get_tags_in_window(tx_sob_tags, 0, 0, noutput_items, d_tx_sob_tag);

    // if there are no SOB tags found, default to outputting a block of samples
    if (tx_sob_tags.size() == 0) {
      n_samps_to_process = ninput_items[0];

      // making sure block fits in max block size
      n_samps_to_process = std::min(n_samps_to_process, d_max_block_size);

      // generate and send iq packet
      d_logger->debug("no TX SOB tags found. Outputting current block");
      process_output_packet(n_samps_to_process, in);

      // Tell runtime system how many output items we produced.
      consume_each(n_samps_to_process);
      return 0;
    }

    // if the first tx sob tag occurs anywhere other than the first
    // sample of this block, output all samples up to the tag
    if (tx_sob_tags[0].offset != nitems_read(0)) {
      n_samps_to_process = tx_sob_tags[0].offset - nitems_read(0);

      // making sure block fits in max block size
      n_samps_to_process = std::min(n_samps_to_process, d_max_block_size);

      d_logger->debug(
          "first TX SOB tag at offset %ld, nitems_read is %ld. Trying to fast "
          "forward to tag",
          tx_sob_tags[0].offset, nitems_read(0));

      // generate and send iq packet
      process_output_packet(n_samps_to_process, in);

      // Tell runtime system how many output items we produced.
      consume_each(n_samps_to_process);
      return 0;
    }

    // otherwise this tag is on the first sample of this block. Check if there
    // is
    // more than one tx sob tag in this block of samples
    if (tx_sob_tags.size() > 1) {
      // if there's more than one block, only output samples up to the next
      // block
      d_logger->debug(
          "%i TX SOB tags found in this block. Trying to Process from offset "
          "%ld to offset %ld",
          tx_sob_tags.size(), tx_sob_tags[0].offset, tx_sob_tags[1].offset);

      n_samps_to_process = tx_sob_tags[1].offset - tx_sob_tags[0].offset;

      // making sure block fits in max block size
      n_samps_to_process = std::min(n_samps_to_process, d_max_block_size);

    } else {
      // otherwise output all samples in this block
      n_samps_to_process = noutput_items;
    }

    // check for existance of a time tag and that the first tx time tag offset
    // is on the first sample of this block. If so, extract the tag value and
    // update the current timestamp
    std::vector<tag_t> tx_time_tags;
    get_tags_in_window(tx_time_tags, 0, 0, noutput_items, d_tx_time_tag);

    if ((tx_time_tags.size() > 0) &&
        (tx_time_tags[0].offset == nitems_read(0))) {
      uint64_t int_seconds =
          pmt::to_uint64(pmt::tuple_ref(tx_time_tags[0].value, 0));
      double frac_seconds =
          pmt::to_double(pmt::tuple_ref(tx_time_tags[0].value, 1));

      uhd::time_spec_t new_time(int_seconds, frac_seconds);

      // adding 0.1 of a sample to the time test to account for meaningless
      // precision issues
      if (new_time + 0.1 / d_sample_rate >= d_block_time) {
        d_logger->debug("updating block time to match tag: %i %f s",
                        int_seconds, frac_seconds);
      } else {
        d_logger->warn(
            "TX SOB mode: block time of %i %f is ahead of "
            "tag time: %i "
            "%f s, this may indicate a math error in tx_time tag inputs, "
            "updating block time",
            d_block_time.get_full_secs(), d_block_time.get_frac_secs(),
            int_seconds, frac_seconds);
      }
      d_block_time = new_time;
    }
    // TODO: Warn that we're ignoring this TX time tag if the offset doesn't
    // match up

    // otherwise the default behavior won't modify the current internal time of
    // this block

    // generate and send iq packet
    d_logger->debug("outputting packet in TX SOB tag mode");
    process_output_packet(n_samps_to_process, in);

    // Tell runtime system how many output items we produced.
    consume_each(n_samps_to_process);
    return 0;
  }
}

} /* namespace envsim */
} /* namespace gr */
