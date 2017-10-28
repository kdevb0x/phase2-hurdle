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

#ifndef INCLUDED_ENVSIM_TX_TIME_TAGGER_IMPL_H
#define INCLUDED_ENVSIM_TX_TIME_TAGGER_IMPL_H

#include <envsim/tx_time_tagger.h>
#include <uhd/usrp/multi_usrp.hpp>

namespace gr {
namespace envsim {

class tx_time_tagger_impl : public tx_time_tagger {
 private:
  // used to update the packet timestamp for each block
  double d_samp_rate;

  pmt::pmt_t d_tx_time_tag;

  // used to track what timestamp we should put on packets
  uhd::time_spec_t d_block_time;

  // for copying data from input to output
  int d_itemsize;

 protected:
  int calculate_output_stream_length(const gr_vector_int &ninput_items);

 public:
  tx_time_tagger_impl(int start_time_int_s, double start_time_frac_s,
                      double samp_rate, const std::string length_tag_key);
  ~tx_time_tagger_impl();

  // Where all the action really happens
  int work(int noutput_items, gr_vector_int &ninput_items,
           gr_vector_const_void_star &input_items,
           gr_vector_void_star &output_items);
};

}  // namespace envsim
}  // namespace gr

#endif /* INCLUDED_ENVSIM_TX_TIME_TAGGER_IMPL_H */
