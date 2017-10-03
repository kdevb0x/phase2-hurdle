/* -*- c++ -*- */
/*
 * Copyright 2017 DARPA.
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

#ifndef INCLUDED_ENVSIM_ENVSIM_SOURCE_H
#define INCLUDED_ENVSIM_ENVSIM_SOURCE_H

#include <envsim/api.h>
#include <gnuradio/sync_block.h>
#include <pmt/pmt.h>

namespace gr {
namespace envsim {

/*!
 * \brief Enforces soft real time constraints for bursty packet transmission
 * \ingroup envsim
 *
 */
class ENVSIM_API envsim_source : virtual public gr::sync_block {
 public:
  typedef boost::shared_ptr<envsim_source> sptr;

  /*!
   * \brief Return a shared_ptr to a new instance of envsim::envsim_source.
   *
   * To avoid accidental use of raw pointers, envsim::envsim_source's
   * constructor is in a private implementation
   * class. envsim::envsim_source::make is the public interface for
   * creating new instances.
   */
  static sptr make(double sample_rate);

  // add getter and setter for internal time field, intended
  // to be used for testability only
  virtual void set_start_time(int64_t start_time_s, int64_t start_time_ps) = 0;
  virtual pmt::pmt_t start_time() = 0;
};

}  // namespace envsim
}  // namespace gr

#endif /* INCLUDED_ENVSIM_ENVSIM_SOURCE_H */
