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

#ifndef INCLUDED_ENVSIM_ENV_SINK_H
#define INCLUDED_ENVSIM_ENV_SINK_H

#include <envsim/api.h>
#include <envsim/env_block.h>
#include <gnuradio/block.h>
namespace gr {
namespace envsim {

/*!
 * \brief <+description of block+>
 * \ingroup envsim
 *
 */
class ENVSIM_API env_sink : virtual public env_block, virtual public gr::block {
 public:
  typedef boost::shared_ptr<env_sink> sptr;

  /*!
   * \brief Return a shared_ptr to a new instance of envsim::env_sink.
   *
   * To avoid accidental use of raw pointers, envsim::env_sink's
   * constructor is in a private implementation
   * class. envsim::env_sink::make is the public interface for
   * creating new instances.
   */
  static sptr make(const std::string &event_name, unsigned int max_block_size,
                   int64_t schedule_offset_ps, double sample_rate,
                   const std::string tx_pkt_len_name);
};

}  // namespace envsim
}  // namespace gr

#endif /* INCLUDED_ENVSIM_ENV_SINK_H */
