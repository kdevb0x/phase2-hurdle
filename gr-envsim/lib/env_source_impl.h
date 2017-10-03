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

#ifndef INCLUDED_ENVSIM_ENV_SOURCE_IMPL_H
#define INCLUDED_ENVSIM_ENV_SOURCE_IMPL_H

#include <envsim/env_source.h>
#include "env_block_impl.h"

namespace gr {
namespace envsim {

class env_source_impl : public env_source, public env_block_impl {
 private:
  size_t d_itemsize;
  pmt::pmt_t d_curr_meta;
  pmt::pmt_t d_curr_vect;
  size_t d_curr_len;

 public:
  env_source_impl(const std::string &tsb_tag_key);
  ~env_source_impl();

  int calculate_output_stream_length(const gr_vector_int &ninput_items);

  int work(int noutput_items, gr_vector_int &ninput_items,
           gr_vector_const_void_star &input_items,
           gr_vector_void_star &output_items);
};

}  // namespace envsim
}  // namespace gr

#endif /* INCLUDED_ENVSIM_ENV_SOURCE_IMPL_H */
