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

#include <gnuradio/blocks/pdu.h>
#include <gnuradio/io_signature.h>
#include "socket_meta_pdu_impl.h"

namespace gr {
namespace envsim {

socket_meta_pdu::sptr socket_meta_pdu::make(std::string type, std::string addr,
                                            std::string port,
                                            int MTU /*= 10000*/,
                                            bool tcp_no_delay /*= false*/) {
  return gnuradio::get_initial_sptr(
      new socket_meta_pdu_impl(type, addr, port, MTU, tcp_no_delay));
}

/*
 * The private constructor
 */
socket_meta_pdu_impl::socket_meta_pdu_impl(std::string type, std::string addr,
                                           std::string port,
                                           int MTU /*= 10000*/,
                                           bool tcp_no_delay /*= false*/)
    : gr::block("socket_meta_pdu", io_signature::make(0, 0, 0),
                io_signature::make(0, 0, 0)),
      d_tcp_no_delay(tcp_no_delay) {
  d_rxbuf.resize(MTU);

  message_port_register_in(PDU_PORT_ID);
  message_port_register_out(PDU_PORT_ID);

  if ((type == "UDP_SERVER") &&
      ((addr.empty()) || (addr == "0.0.0.0"))) {  // Bind on all interfaces
    int port_num = atoi(port.c_str());
    if (port_num == 0)
      throw std::invalid_argument(
          "gr::blocks:socket_pdu: invalid port for UDP_SERVER");
    d_udp_endpoint =
        boost::asio::ip::udp::endpoint(boost::asio::ip::udp::v4(), port_num);
  } else if ((type == "UDP_SERVER") || (type == "UDP_CLIENT")) {
    boost::asio::ip::udp::resolver resolver(d_io_service);
    boost::asio::ip::udp::resolver::query query(
        boost::asio::ip::udp::v4(), addr, port,
        boost::asio::ip::resolver_query_base::passive);

    if (type == "UDP_SERVER")
      d_udp_endpoint = *resolver.resolve(query);
    else
      d_udp_endpoint_other = *resolver.resolve(query);
  }

  if (type == "UDP_SERVER") {
    d_udp_socket.reset(
        new boost::asio::ip::udp::socket(d_io_service, d_udp_endpoint));
    d_udp_socket->async_receive_from(
        boost::asio::buffer(&d_rxbuf[0], d_rxbuf.capacity()),
        d_udp_endpoint_other,
        boost::bind(&socket_meta_pdu_impl::handle_udp_read, this,
                    boost::asio::placeholders::error,
                    boost::asio::placeholders::bytes_transferred));

    d_logger->debug("Server listening for traffic at %s",
                    d_udp_endpoint.address().to_string().c_str());

    set_msg_handler(PDU_PORT_ID,
                    boost::bind(&socket_meta_pdu_impl::udp_send, this, _1));
  } else if (type == "UDP_CLIENT") {
    d_udp_socket.reset(
        new boost::asio::ip::udp::socket(d_io_service, d_udp_endpoint));
    d_udp_socket->async_receive_from(
        boost::asio::buffer(&d_rxbuf[0], d_rxbuf.capacity()),
        d_udp_endpoint_other,
        boost::bind(&socket_meta_pdu_impl::handle_udp_read, this,
                    boost::asio::placeholders::error,
                    boost::asio::placeholders::bytes_transferred));

    d_logger->debug("Client listening for traffic from %s",
                    d_udp_endpoint_other.address().to_string().c_str());

    set_msg_handler(PDU_PORT_ID,
                    boost::bind(&socket_meta_pdu_impl::udp_send, this, _1));
  } else
    throw std::runtime_error("envsim:socket_meta_pdu: unknown socket type");

  d_thread = gr::thread::thread(
      boost::bind(&socket_meta_pdu_impl::run_io_service, this));
  d_started = true;
}

socket_meta_pdu_impl::~socket_meta_pdu_impl() { stop(); }

bool socket_meta_pdu_impl::stop() {
  if (d_started) {
    d_io_service.stop();
    d_thread.interrupt();
    d_thread.join();
  }
  d_started = false;
  return true;
}

void socket_meta_pdu_impl::udp_send(pmt::pmt_t msg) {
  if (d_udp_endpoint_other.address().to_string() == "0.0.0.0") {
    d_logger->warn(
        "for socket listening at %s , port %i, other endpoint not configured. "
        "Skipping message send",
        d_udp_endpoint.address().to_string().c_str(), d_udp_endpoint.port());
    return;
  }

  // pmt::pmt_t vector = pmt::cdr(msg);
  // size_t len = pmt::blob_length(vector);

  // grab entire pmt, including metadata
  std::string txbuf = pmt::serialize_str(msg);

  if (txbuf.length() > d_rxbuf.length()) {
    d_logger->warn("packet length of %i is too large for MTU of %i",
                   txbuf.length(), d_rxbuf.length());
    throw std::runtime_error(
        "envsim:socket_meta_pdu: PDU does not fit in a single packet MTU");
  }

  // d_logger->debug("sending packet");
  d_udp_socket->send_to(boost::asio::buffer(txbuf), d_udp_endpoint_other);
}

void socket_meta_pdu_impl::handle_udp_read(
    const boost::system::error_code& error, size_t bytes_transferred) {
  if (!error) {
    pmt::pmt_t pdu = pmt::deserialize_str(d_rxbuf);

    message_port_pub(PDU_PORT_ID, pdu);

    d_udp_socket->async_receive_from(
        boost::asio::buffer(&d_rxbuf[0], d_rxbuf.capacity()),
        d_udp_endpoint_other,
        boost::bind(&socket_meta_pdu_impl::handle_udp_read, this,
                    boost::asio::placeholders::error,
                    boost::asio::placeholders::bytes_transferred));
  }
}

} /* namespace envsim */
} /* namespace gr */
