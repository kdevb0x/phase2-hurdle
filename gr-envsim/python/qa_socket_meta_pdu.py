#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2017 <+YOU OR YOUR COMPANY+>.
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from gnuradio import gr, gr_unittest
from gnuradio import blocks

import pmt
import random
import time

import envsim_swig as envsim

class qa_socket_meta_pdu (gr_unittest.TestCase):

    def setUp (self):
        self.tb = gr.top_block ()

    def tearDown (self):
        self.tb = None

    def test_001 (self):
        # Send a PDU through a pair of UDP sockets
        port = str(random.Random().randint(0, 30000) + 10000)
        srcdata = (0x64, 0x6f, 0x67, 0x65)
        data = pmt.init_u8vector(srcdata.__len__(), srcdata)
        meta = pmt.to_pmt({"this":"is",
                           "a metadata":"dict"})
        pdu_msg = pmt.cons(meta, data)

        self.pdu_source = blocks.message_strobe(pdu_msg, 500)
        self.pdu_recv = envsim.socket_meta_pdu("UDP_SERVER", "localhost", port)
        self.pdu_send = envsim.socket_meta_pdu("UDP_CLIENT", "localhost", port)

        self.dbg = blocks.message_debug()

        self.tb.msg_connect(self.pdu_source, "strobe", self.pdu_send, "pdus")
        self.tb.msg_connect(self.pdu_recv, "pdus", self.dbg, "store")

        self.tb.start ()
        time.sleep(1)
        self.tb.stop()
        self.tb.wait()
        self.pdu_send = None
        self.pdu_recv = None

        received = self.dbg.get_message(0)
        received_data = pmt.cdr(received)
        msg_data = []
        for i in xrange(4):
            msg_data.append(pmt.u8vector_ref(received_data, i))
        self.assertEqual(srcdata, tuple(msg_data))


if __name__ == '__main__':
    gr_unittest.run(qa_socket_meta_pdu)
