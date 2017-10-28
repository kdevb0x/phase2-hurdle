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

#ifndef INCLUDED_ENVSIM_ZMQ_ENVSIM_SOURCE_H
#define INCLUDED_ENVSIM_ZMQ_ENVSIM_SOURCE_H

#include <envsim/api.h>
#include <gnuradio/sync_block.h>

namespace gr {
namespace envsim {

/*!
 * \brief <+description of block+>
 * \ingroup envsim
 *
 */
class ENVSIM_API zmq_envsim_source : virtual public gr::sync_block {
 public:
  typedef boost::shared_ptr<zmq_envsim_source> sptr;

  /*!
   * \brief Return a shared_ptr to a new instance of envsim::zmq_envsim_source.
   *
   * To avoid accidental use of raw pointers, envsim::zmq_envsim_source's
   * constructor is in a private implementation
   * class. envsim::zmq_envsim_source::make is the public interface for
   * creating new instances.
   */
  static sptr make(char *address, int timeout = 100, int hwm = -1,
                   double sample_rate = 1e6, int start_time_int_s = 0,
                   double start_time_frac_s = 0);
};

}  // namespace envsim
}  // namespace gr

#endif /* INCLUDED_ENVSIM_ZMQ_ENVSIM_SOURCE_H */
