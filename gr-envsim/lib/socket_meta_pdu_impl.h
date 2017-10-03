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

#ifndef INCLUDED_ENVSIM_SOCKET_META_PDU_IMPL_H
#define INCLUDED_ENVSIM_SOCKET_META_PDU_IMPL_H

#include <envsim/socket_meta_pdu.h>
#include <boost/asio.hpp>
#include "stream_pdu_base.h"

namespace gr {
  namespace envsim {

    class socket_meta_pdu_impl : public socket_meta_pdu
    {
     private:
      boost::asio::io_service d_io_service;
      std::string d_rxbuf;
      void run_io_service() { d_io_service.run(); }
      gr::thread::thread d_thread;
      bool d_started;
      bool d_finished;

      bool d_tcp_no_delay;

      // UDP specific
      boost::asio::ip::udp::endpoint d_udp_endpoint;
      boost::asio::ip::udp::endpoint d_udp_endpoint_other;
      boost::shared_ptr<boost::asio::ip::udp::socket> d_udp_socket;
      void handle_udp_read(const boost::system::error_code& error, size_t bytes_transferred);
      void udp_send(pmt::pmt_t msg);

     public:
      socket_meta_pdu_impl(std::string type, std::string addr, std::string port, int MTU = 10000, bool tcp_no_delay = false);
      ~socket_meta_pdu_impl();
      bool stop();

    };

  } // namespace envsim
} // namespace gr

#endif /* INCLUDED_ENVSIM_SOCKET_META_PDU_IMPL_H */

