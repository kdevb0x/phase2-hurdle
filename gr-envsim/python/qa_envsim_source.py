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
import envsim_swig as envsim

import pmt
import numpy as np

from test_utils import *


class qa_envsim_source (gr_unittest.TestCase):

    def setUp (self):
        self.tb = gr.top_block ()

    def tearDown (self):
        self.tb = None

    def test_set_start_time (self):

        samp_rate = 1e6

        expected_time_s = 10
        expected_time_ps = 1000

        op = envsim.envsim_source(samp_rate)

        # set our start time
        op.set_start_time(expected_time_s, expected_time_ps)

        # read back the result
        # (result_time_s, result_time_ps) =  op.start_time()
        result = pmt.to_python(op.start_time())


        self.assertEqual(expected_time_s, result[0])
        self.assertEqual(expected_time_ps, result[1])

    def test_packet_insert (self):


        # set up test limits

        # only collect 20 samples
        sample_lim = 20
        samp_rate = 1e6

        block_start_s = 100
        block_start_ps = 5* int(1e12/samp_rate)

        # set up input packet struct
        num_samps = 5
        packet_start_time = (100, 10* int(1e12/samp_rate))

        iq_pkt_dict = {
            "meta":{
                "timestamp_s":packet_start_time,
                "packet_len":num_samps
            },
            "data":list(np.array(range(num_samps), dtype=np.complex))
        }

        iq_pkt = dict_to_iq_packet(iq_pkt_dict)

        # set up our expected output
        expected = np.concatenate( (np.array( [0,]*5, dtype=np.complex ),
                                    np.array(range(num_samps), dtype=np.complex),
                                    np.array( [0,]*10, dtype=np.complex)) )

        # set up flowgraph blocks
        op = envsim.envsim_source(samp_rate)
        head = blocks.head(gr.sizeof_gr_complex*1, sample_lim)
        dst = blocks.vector_sink_c()

        # make connections
        self.tb.connect(op,head,dst)

        # set source block's time
        op.set_start_time(block_start_s, block_start_ps)

        # publish our pmt message before the flowgraph starts to
        # avoid a race condition

        op.to_basic_block()._post(pmt.intern("packets"), iq_pkt)

        self.tb.run ()
        # check data

        result = dst.data()

        self.assertListEqual(list(expected), list(result))

if __name__ == '__main__':
    gr_unittest.run(qa_envsim_source, "qa_envsim_source.xml")
