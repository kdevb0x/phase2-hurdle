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
#include "tx_time_tagger_impl.h"

namespace gr {
namespace envsim {

tx_time_tagger::sptr tx_time_tagger::make(int start_time_int_s,
                                          double start_time_frac_s,
                                          double samp_rate,
                                          const std::string length_tag_key) {
  return gnuradio::get_initial_sptr(new tx_time_tagger_impl(
      start_time_int_s, start_time_frac_s, samp_rate, length_tag_key));
}

/*
 * The private constructor
 */
tx_time_tagger_impl::tx_time_tagger_impl(int start_time_int_s,
                                         double start_time_frac_s,
                                         double samp_rate,
                                         const std::string length_tag_key)
    : gr::tagged_stream_block(
          "tx_time_tagger", gr::io_signature::make(1, 1, sizeof(gr_complex)),
          gr::io_signature::make(1, 1, sizeof(gr_complex)), length_tag_key),
      d_samp_rate(samp_rate),
      d_block_time(start_time_int_s, start_time_frac_s),
      d_itemsize(sizeof(gr_complex)) {
  // store off the symbol to use for tx time tags
  d_tx_time_tag = pmt::intern("tx_time");
}

/*
  * Our virtual destructor.
  */
tx_time_tagger_impl::~tx_time_tagger_impl() {}

int tx_time_tagger_impl::calculate_output_stream_length(
    const gr_vector_int &ninput_items) {
  return ninput_items[0];
}

int tx_time_tagger_impl::work(int noutput_items, gr_vector_int &ninput_items,
                              gr_vector_const_void_star &input_items,
                              gr_vector_void_star &output_items) {
  const char *signal = (const char *)input_items[0];
  char *out = (char *)output_items[0];

  memcpy(out, signal, noutput_items * d_itemsize);

  d_logger->debug("n input items: %i", ninput_items[0]);

  // Add tx_time tag to the start of every tagged block
  add_item_tag(0, nitems_written(0), d_tx_time_tag,
               pmt::make_tuple(pmt::from_uint64(d_block_time.get_full_secs()),
                               pmt::from_double(d_block_time.get_frac_secs())));

  d_logger->debug("sent packet with time %i %f s", d_block_time.get_full_secs(),
                  d_block_time.get_frac_secs());

  // update the block time
  d_block_time = d_block_time + ninput_items[0] / d_samp_rate;

  d_logger->debug("block time updated to %i %f s", d_block_time.get_full_secs(),
                  d_block_time.get_frac_secs());

  // Tell runtime system how many output items we produced.
  return ninput_items[0];
}

} /* namespace envsim */
} /* namespace gr */
