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

#include "env_block_impl.h"
#include <boost/make_shared.hpp>

namespace gr {
namespace envsim {

/**********************************************************************
 * Structors
 *********************************************************************/
// env_block::env_block()
//     : gr::sync_block("env_block",
//                      gr::io_signature::make(1, 1, sizeof(gr_complex)),
//                      gr::io_signature::make(0, 0, 0)) {}

env_block_impl::env_block_impl() {}

env_block_impl::~env_block_impl() {
  // nop
}

// /**********************************************************************
//  * Public API calls
//  *********************************************************************/

/**********************************************************************
  * Public API calls (see usrp_block.h for docs)
  **********************************************************************/
// Getters
uhd::sensor_value_t env_block_impl::get_mboard_sensor(const std::string &name,
                                                      size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

std::vector<std::string> env_block_impl::get_mboard_sensor_names(
    size_t mboard) {
  std::vector<std::string> result;
  return result;
}

std::string env_block_impl::get_time_source(const size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

std::vector<std::string> env_block_impl::get_time_sources(const size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

std::string env_block_impl::get_clock_source(const size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

std::vector<std::string> env_block_impl::get_clock_sources(
    const size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

double env_block_impl::get_clock_rate(size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

uhd::time_spec_t env_block_impl::get_time_now(size_t mboard = 0) {
  struct timeval tv1;
  gettimeofday(&tv1, NULL);
  // TODO: Consider adding a time delta set by set_time.....
  return uhd::time_spec_t(tv1.tv_sec, double(tv1.tv_usec) / 1e6);

  // return d_block_time;
}

uhd::time_spec_t env_block_impl::get_time_last_pps(size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

uhd::usrp::multi_usrp::sptr env_block_impl::get_device(void) {
  throw std::runtime_error("Not Yet Implemented");
}

std::vector<std::string> env_block_impl::get_gpio_banks(const size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

boost::uint32_t env_block_impl::get_gpio_attr(const std::string &bank,
                                              const std::string &attr,
                                              const size_t mboard = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

size_t env_block_impl::get_num_mboards() {
  throw std::runtime_error("Not Yet Implemented");
}

std::string env_block_impl::get_subdev_spec(size_t mboard = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

double env_block_impl::get_samp_rate(void) {
  throw std::runtime_error("Not Yet Implemented");
}

uhd::meta_range_t env_block_impl::get_samp_rates(void) {
  throw std::runtime_error("Not Yet Implemented");
}

double env_block_impl::get_center_freq(size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

uhd::freq_range_t env_block_impl::get_freq_range(size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

double env_block_impl::get_gain(size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

double env_block_impl::get_gain(const std::string &name, size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

double env_block_impl::get_normalized_gain(size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

std::vector<std::string> env_block_impl::get_gain_names(size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

uhd::gain_range_t env_block_impl::get_gain_range(size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

uhd::gain_range_t env_block_impl::get_gain_range(const std::string &name,
                                                 size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

std::string env_block_impl::get_antenna(size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

std::vector<std::string> env_block_impl::get_antennas(size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

double env_block_impl::get_bandwidth(size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

uhd::freq_range_t env_block_impl::get_bandwidth_range(size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

uhd::sensor_value_t env_block_impl::get_sensor(const std::string &name,
                                               size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

std::vector<std::string> env_block_impl::get_sensor_names(size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

uhd::usrp::dboard_iface::sptr env_block_impl::get_dboard_iface(
    size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

// Setters
void env_block_impl::set_clock_config(const uhd::clock_config_t &clock_config,
                                      size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

void env_block_impl::set_time_source(const std::string &source,
                                     const size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

void env_block_impl::set_clock_source(const std::string &source,
                                      const size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

void env_block_impl::set_clock_rate(double rate, size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

void env_block_impl::set_time_now(const uhd::time_spec_t &time_spec,
                                  size_t mboard) {
  // d_block_time = time_spec;

  return;
}

void env_block_impl::set_time_next_pps(const uhd::time_spec_t &time_spec) {
  throw std::runtime_error("Not Yet Implemented");
}

void env_block_impl::set_time_unknown_pps(const uhd::time_spec_t &time_spec) {
  throw std::runtime_error("Not Yet Implemented");
}

void env_block_impl::set_command_time(const uhd::time_spec_t &time_spec,
                                      size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

void env_block_impl::set_user_register(const uint8_t addr, const uint32_t data,
                                       size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

void env_block_impl::clear_command_time(size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

void env_block_impl::set_gpio_attr(const std::string &bank,
                                   const std::string &attr,
                                   const boost::uint32_t value,
                                   const boost::uint32_t mask,
                                   const size_t mboard) {
  throw std::runtime_error("Not Yet Implemented");
}

void env_block_impl::set_subdev_spec(const std::string &spec, size_t mboard) {
  // GR_LOG_WARN(d_logger, "set_subdev_spec currently does nothing");
  return;
}

void env_block_impl::set_samp_rate(double rate) {
  // GR_LOG_WARN(d_logger, "set_samp_rate currently does nothing");
  return;
}
uhd::tune_result_t env_block_impl::set_center_freq(
    const uhd::tune_request_t tune_request, size_t chan) {
  // GR_LOG_WARN(d_logger, "set_center_freq currently does nothing");

  uhd::tune_result_t result{};
  result.clipped_rf_freq = tune_request.target_freq;
  result.target_rf_freq = tune_request.target_freq;
  result.actual_rf_freq = tune_request.target_freq;
  result.target_dsp_freq = tune_request.target_freq;
  result.actual_dsp_freq = tune_request.target_freq;

  return result;
}
void env_block_impl::set_gain(double gain, size_t chan) {
  // GR_LOG_WARN(d_logger, "set_gain currently does nothing");
  return;
}
void env_block_impl::set_gain(double gain, const std::string &name,
                              size_t chan) {
  // GR_LOG_WARN(d_logger, "set_gain currently does nothing");
  return;
}

void env_block_impl::set_normalized_gain(double norm_gain, size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

void env_block_impl::set_antenna(const std::string &ant, size_t chan) {
  // GR_LOG_WARN(d_logger, "set_antenna currently does nothing");
  return;
}

void env_block_impl::set_bandwidth(double bandwidth, size_t chan = 0) {
  throw std::runtime_error("Not Yet Implemented");
}

void env_block_impl::set_stream_args(const uhd::stream_args_t &stream_args) {
  throw std::runtime_error("Not Yet Implemented");
}

} /* namespace envsim */
} /* namespace gr */