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

#ifndef INCLUDED_ENVSIM_ENV_SINK_IMPL_H
#define INCLUDED_ENVSIM_ENV_SINK_IMPL_H

#include <envsim/env_sink.h>
#include "env_block_impl.h"
#include "iq_packet.h"

#include <cstring>
#include <sstream>
#include <zmq.hpp>

#define TX_TIME_NAME "tx_time"
#define TX_SOB_NAME "tx_sob"
#define TX_EOB_NAME "tx_eob"

namespace gr {
namespace envsim {

class env_sink_impl : public env_sink, public env_block_impl {
 private:
  // this is the largest segment we'll send at once. Anything larger than this
  // will be
  // split up into multiple blocks
  int d_max_block_size;
  int64_t d_schedule_offset_ps;  // deprecated
  unsigned int d_itemsize;

  // used to track what timestamp we should put on packets
  uhd::time_spec_t d_block_time;

  // this tracks the number of samples
  int d_remaining_samps_in_burst;

  // this tracks the current packet counter
  int d_packet_counter;

  //   // add some variables used to convert between wall time
  //   // and sample counts
  //   int64_t d_start_time_s;
  //   int64_t d_start_time_ps;
  bool d_time_initialized;

  bool d_first_iteration;

  double d_sample_rate;

  // store the name of this event
  const std::string d_event_name;

  // store off list of tx tags we will be working with
  pmt::pmt_t d_tx_time_tag;
  pmt::pmt_t d_tx_pkt_len_tag;
  pmt::pmt_t d_tx_sob_tag;
  pmt::pmt_t d_tx_eob_tag;

  std::vector<pmt::pmt_t> d_event_list;

  bool d_using_pkt_len_tags;

  // zmq specific items
  zmq::context_t *d_context;
  zmq::socket_t *d_socket;
  size_t d_vsize;
  int d_timeout;

  void process_output_packet(int n_samps_to_process, const gr_complex *in);

  void send_message(const void *in_buf, const int msg_len);

 public:
  env_sink_impl(const std::string &event_name, unsigned int max_burst_size,
                int64_t schedule_offset_ps, double sample_rate,
                const std::string tx_pkt_len_name, char *address,
                int timeout = 100, int hwm = -1);
  ~env_sink_impl();

  void forecast(int noutput_items, gr_vector_int &ninput_items_required);

  int general_work(int noutput_items, gr_vector_int &ninput_items,
                   gr_vector_const_void_star &input_items,
                   gr_vector_void_star &output_items);
};

}  // namespace envsim
}  // namespace gr

#endif /* INCLUDED_ENVSIM_ENV_SINK_IMPL_H */
