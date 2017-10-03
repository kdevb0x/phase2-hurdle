/* -*- c++ -*- */
/*
 * Copyright 2015 Free Software Foundation, Inc.
 *
 * This file is part of GNU Radio
 *
 * GNU Radio is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * GNU Radio is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with GNU Radio; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifndef INCLUDED_GR_ENV_BLOCK_IMPL_H
#define INCLUDED_GR_ENV_BLOCK_IMPL_H

#include <envsim/env_block.h>
#include <pmt/pmt.h>
#include <sys/time.h>
#include <boost/bind.hpp>
#include <uhd/usrp/multi_usrp.hpp>

namespace gr {
namespace envsim {

class env_block_impl : virtual public env_block {
 public:
  /**********************************************************************
    * Public API calls (see usrp_block.h for docs)
    **********************************************************************/
  // Getters
  uhd::sensor_value_t get_mboard_sensor(const std::string &name, size_t mboard);
  std::vector<std::string> get_mboard_sensor_names(size_t mboard);
  std::string get_time_source(const size_t mboard);
  std::vector<std::string> get_time_sources(const size_t mboard);
  std::string get_clock_source(const size_t mboard);
  std::vector<std::string> get_clock_sources(const size_t mboard);
  double get_clock_rate(size_t mboard);
  uhd::time_spec_t get_time_now(size_t mboard);
  uhd::time_spec_t get_time_last_pps(size_t mboard);
  uhd::usrp::multi_usrp::sptr get_device(void);
  std::vector<std::string> get_gpio_banks(const size_t mboard);
  boost::uint32_t get_gpio_attr(const std::string &bank,
                                const std::string &attr, const size_t mboard);
  size_t get_num_mboards();

  std::string get_subdev_spec(size_t mboard);
  double get_samp_rate(void);
  uhd::meta_range_t get_samp_rates(void);
  double get_center_freq(size_t chan);
  uhd::freq_range_t get_freq_range(size_t chan);
  double get_gain(size_t chan);
  double get_gain(const std::string &name, size_t chan);
  double get_normalized_gain(size_t chan);
  std::vector<std::string> get_gain_names(size_t chan);
  uhd::gain_range_t get_gain_range(size_t chan);
  uhd::gain_range_t get_gain_range(const std::string &name, size_t chan);
  std::string get_antenna(size_t chan);
  std::vector<std::string> get_antennas(size_t chan);
  double get_bandwidth(size_t chan);
  uhd::freq_range_t get_bandwidth_range(size_t chan);

  uhd::sensor_value_t get_sensor(const std::string &name, size_t chan);
  std::vector<std::string> get_sensor_names(size_t chan);
  uhd::usrp::dboard_iface::sptr get_dboard_iface(size_t chan);

  // Setters
  void set_clock_config(const uhd::clock_config_t &clock_config, size_t mboard);
  void set_time_source(const std::string &source, const size_t mboard);
  void set_clock_source(const std::string &source, const size_t mboard);
  void set_clock_rate(double rate, size_t mboard);
  void set_time_now(const uhd::time_spec_t &time_spec, size_t mboard);
  void set_time_next_pps(const uhd::time_spec_t &time_spec);
  void set_time_unknown_pps(const uhd::time_spec_t &time_spec);
  void set_command_time(const uhd::time_spec_t &time_spec, size_t mboard);
  void set_user_register(const uint8_t addr, const uint32_t data,
                         size_t mboard);
  void clear_command_time(size_t mboard);
  void set_gpio_attr(const std::string &bank, const std::string &attr,
                     const boost::uint32_t value, const boost::uint32_t mask,
                     const size_t mboard);

  void set_subdev_spec(const std::string &spec, size_t mboard);

  void set_samp_rate(double rate);

  uhd::tune_result_t set_center_freq(const uhd::tune_request_t tune_request,
                                     size_t chan);

  void set_gain(double gain, size_t chan);

  void set_gain(double gain, const std::string &name, size_t chan);

  void set_normalized_gain(double norm_gain, size_t chan);

  void set_antenna(const std::string &ant, size_t chan);

  void set_bandwidth(double bandwidth, size_t chan);

  void set_stream_args(const uhd::stream_args_t &stream_args);

  /**********************************************************************
   * Structors
   * ********************************************************************/
  virtual ~env_block_impl();

 protected:
  // add some variables used to convert between wall time
  // and sample counts

  env_block_impl();
};

} /* namespace uhd */
} /* namespace gr */

#endif /* INCLUDED_GR_ENV_BLOCK_IMPL_H */
