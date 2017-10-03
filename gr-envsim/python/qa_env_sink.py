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
from envsim import time_spec_t


# OK what do we really need to test to believe this thing works?


# Check that it handles processing tagged stream chunks that span
# more than one work function call - TBD


# check that a burst gets sent out to fast forward to the
# start of the tx burst if we get a tx sob tag that
# does not occur at the start of the sample block in the
# work function

# check that a burst gets sent out if we're using the tx SOB tag, but don't include a tx_time

# check that a burst gets sent out if we're using the tx SOB tag, and include a tx_time

import sys
import time

import test_utils
from test_utils import *

ACCEPTABLE_TIME_DIGITS_OF_ACCURACY = 3 # we should be able to hit timing within a millisecond

sys.stdout = test_utils.Unbuffered(sys.stdout)


class qa_env_sink (test_utils.EnvSimAssertions):

    def setUp (self):
        self.tb = gr.top_block ()

        self.tx_pkt_len_name = "burst_len"
        self.tx_time_name = "tx_time"
        self.tx_sob_name = "tx_sob"

        self.default_inputs = {"event_name":"tx_burst",
                               "max_block_size":4096,
                               "schedule_offset_ps":0,
                               "sample_rate":1e6,
                               "tx_pkt_len_name":"" # default to no burst tag
                              }

        # we'll want this for most tests so set it up here
        self.msg_dst = blocks.message_debug()

    def tearDown (self):
        self.tb = None


    def test_set_time_now (self):

        # initialize the block and set the start time
        print("starting set time now")

        sink_inputs = dict(self.default_inputs)
        int_s = 1503689677
        frac_s = 0.5
        op = envsim.env_sink(**sink_inputs)
        op.set_time_now(time_spec_t(int_s, frac_s))
        uhd_time_now = op.get_time_now()

        self.assertEqual(int_s, uhd_time_now.get_full_secs())
        self.assertEqual(frac_s, uhd_time_now.get_frac_secs())


    def test_start_time_on_init (self):

        # initialize the block and get the start time
        print("starting start time on init")

        sink_inputs = dict(self.default_inputs)



        op = envsim.env_sink(**sink_inputs)
        now = time.time()
        uhd_time_now = op.get_time_now()

        self.assertAlmostEqual(uhd_time_now.get_real_secs(), now,
                               places=ACCEPTABLE_TIME_DIGITS_OF_ACCURACY)


    def test_tagged_bursts_no_tags (self):
        '''
        The packet length field is defined.

        We input no stream tags.

        Check that a message is generated including all input samples
        and appropriate timestamps
        '''

        print("starting tagged bursts no tags")

        # put in a known (and easy to do math on) start time to make testing doable
        start_time_int_s = 100
        start_time_frac_s = 0.0

        sink_inputs = dict(self.default_inputs)
        sink_inputs["tx_pkt_len_name"] = "burst_len"

        sample_rate = sink_inputs["sample_rate"]

        src_data = [0 + 1j, 2 + 3j, 4 +5j, 6 + 7j,]

        expected_list = [
            {
                "meta":{
                    "timestamp_s":(start_time_int_s,int(start_time_frac_s*1e12)),
                    "packet_len":len(src_data)
                },
                "data":src_data
            },
        ]

        expected_block_time = start_time_int_s + start_time_frac_s + len(src_data)/sample_rate

        # note no tags used
        src = blocks.vector_source_c(src_data)
        op = envsim.env_sink(**sink_inputs)

        # set start time instead of getting from system clock
        op.set_time_now(time_spec_t(start_time_int_s, start_time_frac_s))

        # connect up input and message destination blocks
        self.tb.connect(src, op)
        self.tb.msg_connect((op, 'event'), (self.msg_dst, 'store'))

        self.tb.run ()
        # check data

        result_list = [iq_packet_to_dict(self.msg_dst.get_message(i)) for i in range(self.msg_dst.num_messages())]

        self.assertPacketListEqual(expected_list, result_list)
        self.assertAlmostEqual(expected_block_time, op.get_time_now().get_real_secs())


    def test_tagged_bursts_fast_forward (self):
        '''
        The packet length field is defined.abs

        We input a packet len tag that occurs mid-sample block.

        We don't include a tx_time tag

        Check that 2 messages are generated including all input samples
        and appropriate timestamps
        '''

        print("starting tagged_bursts fast forward")

        # put in a known (and easy to do math on) start time to make testing doable
        start_time_int_s = 100
        start_time_frac_s = 0.0

        sink_inputs = dict(self.default_inputs)
        sink_inputs["tx_pkt_len_name"] = self.tx_pkt_len_name

        sample_rate = sink_inputs["sample_rate"]

        src_data = [0 + 1j, 2 + 3j, 4 +5j, 6 + 7j,
                    8 + 9j, 10 + 11j, 12 +13j, 14 + 15j, 16 + 17j, 18 + 19j]

        tag_offset = 4

        src_tags = [{"offset":tag_offset,
                     "key":self.tx_pkt_len_name,
                     "value":len(src_data) - tag_offset},]

        # convert src_tags into proper gnuradio stream tags
        src_tags = [dict_to_tag(st) for st in src_tags]

        expected_packet2_time = ( time_spec_t(start_time_int_s,start_time_frac_s) +
                                  time_spec_t(float(tag_offset)/sample_rate) )

        # Note that currently the timestamp for envsim is in units of integer seconds and integer picoseconds
        expected_list = [
            {
                "meta":{
                    "timestamp_s":(start_time_int_s,int(start_time_frac_s*1e12)),
                    "packet_len":tag_offset
                },
                "data":src_data[:tag_offset]
            },
            {
                "meta":{
                    "timestamp_s":(expected_packet2_time.get_full_secs(),
                                   int(expected_packet2_time.get_frac_secs()*1e12)), # update this
                    "packet_len":len(src_data) - tag_offset
                },
                "data":src_data[tag_offset:]
            },
        ]

        expected_block_time = start_time_int_s + start_time_frac_s + len(src_data)/sample_rate

        src = blocks.vector_source_c(src_data, False, 1, src_tags)

        print("length of source data vector: {}".format(len(src_data)))

        op = envsim.env_sink(**sink_inputs)

        # set start time instead of getting from system clock
        op.set_time_now(time_spec_t(start_time_int_s, start_time_frac_s))

        # connect up input and message destination blocks
        self.tb.connect(src, op)
        self.tb.msg_connect((op, 'event'), (self.msg_dst, 'store'))

        self.tb.run ()
        # check data

        result_list = [iq_packet_to_dict(self.msg_dst.get_message(i)) for i in range(self.msg_dst.num_messages())]

        self.assertPacketListEqual(expected_list, result_list)
        self.assertAlmostEqual(expected_block_time, op.get_time_now().get_real_secs())


    def test_tagged_bursts_with_tx_time (self):
        '''
        The packet length field is defined

        We input a packet len tag that occurs on the first sample of the block.

        We include a tx_time tag

        Check that one message is generated including all input samples
        and appropriate timestamp
        '''

        print("starting test_tagged_bursts_with_tx_time")

        # put in a known (and easy to do math on) start time to make testing doable
        start_time_int_s = 100
        start_time_frac_s = 0.0

        tag_start_time_int_s = 200
        tag_start_time_frac_s = 0.5

        sink_inputs = dict(self.default_inputs)
        sink_inputs["tx_pkt_len_name"] = self.tx_pkt_len_name

        sample_rate = sink_inputs["sample_rate"]

        src_data = [0 + 1j, 2 + 3j, 4 +5j, 6 + 7j,
                    8 + 9j, 10 + 11j, 12 +13j, 14 + 15j, 16 + 17j, 18 + 19j]

        tag_offset = 0

        src_tags = [{"offset":tag_offset,
                     "key":self.tx_pkt_len_name,
                     "value":len(src_data)},
                     {"offset":tag_offset,
                     "key":self.tx_time_name,
                     "value":(tag_start_time_int_s, tag_start_time_frac_s)}]

        # convert src_tags into proper gnuradio stream tags
        src_tags = [dict_to_tag(st) for st in src_tags]

        # Note that currently the timestamp for envsim is in units of integer seconds and integer picoseconds
        expected_list = [
            {
                "meta":{
                    "timestamp_s":(tag_start_time_int_s,int(tag_start_time_frac_s*1e12)),
                    "packet_len":len(src_data)
                },
                "data":src_data
            },
        ]

        expected_block_time = tag_start_time_int_s + tag_start_time_frac_s + len(src_data)/sample_rate

        src = blocks.vector_source_c(src_data, False, 1, src_tags)

        print("length of source data vector: {}".format(len(src_data)))

        op = envsim.env_sink(**sink_inputs)

        # set start time instead of getting from system clock
        op.set_time_now(time_spec_t(start_time_int_s, start_time_frac_s))

        # connect up input and message destination blocks
        self.tb.connect(src, op)
        self.tb.msg_connect((op, 'event'), (self.msg_dst, 'store'))

        self.tb.run ()
        # check data

        result_list = [iq_packet_to_dict(self.msg_dst.get_message(i)) for i in range(self.msg_dst.num_messages())]

        self.assertPacketListEqual(expected_list, result_list)
        self.assertAlmostEqual(expected_block_time, op.get_time_now().get_real_secs())


    def test_sob_bursts_no_tags (self):
        '''
        The packet length field is not defined.

        We input no stream tags.

        Check that a message is generated including all input samples
        and appropriate timestamps
        '''

        print("test_sob_bursts_no_tags")

        # put in a known (and easy to do math on) start time to make testing doable
        start_time_int_s = 100
        start_time_frac_s = 0.0

        sink_inputs = dict(self.default_inputs)
        sink_inputs["tx_pkt_len_name"] = ""

        sample_rate = sink_inputs["sample_rate"]

        src_data = [0 + 1j, 2 + 3j, 4 +5j, 6 + 7j,]

        expected_list = [
            {
                "meta":{
                    "timestamp_s":(start_time_int_s,int(start_time_frac_s*1e12)),
                    "packet_len":len(src_data)
                },
                "data":src_data
            },
        ]

        expected_block_time = start_time_int_s + start_time_frac_s + len(src_data)/sample_rate

        # note no tags used
        src = blocks.vector_source_c(src_data)
        op = envsim.env_sink(**sink_inputs)

        # set start time instead of getting from system clock
        op.set_time_now(time_spec_t(start_time_int_s, start_time_frac_s))

        # connect up input and message destination blocks
        self.tb.connect(src, op)
        self.tb.msg_connect((op, 'event'), (self.msg_dst, 'store'))

        self.tb.run ()
        # check data

        result_list = [iq_packet_to_dict(self.msg_dst.get_message(i)) for i in range(self.msg_dst.num_messages())]

        self.assertPacketListEqual(expected_list, result_list)
        self.assertAlmostEqual(expected_block_time, op.get_time_now().get_real_secs())


    def test_sob_bursts_fast_forward (self):
        '''
        The packet length field is not defined

        We input a tx sob tag that occurs mid-sample block.

        We don't include a tx_time tag

        Check that 2 messages are generated including all input samples
        and appropriate timestamps
        '''

        print("test_sob_bursts_fast_forward")

        # put in a known (and easy to do math on) start time to make testing doable
        start_time_int_s = 100
        start_time_frac_s = 0.0

        sink_inputs = dict(self.default_inputs)
        sink_inputs["tx_pkt_len_name"] = ""

        sample_rate = sink_inputs["sample_rate"]

        src_data = [0 + 1j, 2 + 3j, 4 +5j, 6 + 7j,
                    8 + 9j, 10 + 11j, 12 +13j, 14 + 15j, 16 + 17j, 18 + 19j]

        tag_offset = 4

        src_tags = [{"offset":tag_offset,
                     "key":self.tx_sob_name,
                     "value":True},]

        # convert src_tags into proper gnuradio stream tags
        src_tags = [dict_to_tag(st) for st in src_tags]

        expected_packet2_time = ( time_spec_t(start_time_int_s,start_time_frac_s) +
                                  time_spec_t(float(tag_offset)/sample_rate) )

        # Note that currently the timestamp for envsim is in units of integer seconds and integer picoseconds
        expected_list = [
            {
                "meta":{
                    "timestamp_s":(start_time_int_s,int(start_time_frac_s*1e12)),
                    "packet_len":tag_offset
                },
                "data":src_data[:tag_offset]
            },
            {
                "meta":{
                    "timestamp_s":(expected_packet2_time.get_full_secs(),
                                   int(expected_packet2_time.get_frac_secs()*1e12)), # update this
                    "packet_len":len(src_data) - tag_offset
                },
                "data":src_data[tag_offset:]
            },
        ]

        expected_block_time = start_time_int_s + start_time_frac_s + len(src_data)/sample_rate

        src = blocks.vector_source_c(src_data, False, 1, src_tags)

        print("length of source data vector: {}".format(len(src_data)))

        op = envsim.env_sink(**sink_inputs)

        # set start time instead of getting from system clock
        op.set_time_now(time_spec_t(start_time_int_s, start_time_frac_s))

        # connect up input and message destination blocks
        self.tb.connect(src, op)
        self.tb.msg_connect((op, 'event'), (self.msg_dst, 'store'))

        self.tb.run ()
        # check data

        result_list = [iq_packet_to_dict(self.msg_dst.get_message(i)) for i in range(self.msg_dst.num_messages())]

        self.assertPacketListEqual(expected_list, result_list)
        self.assertAlmostEqual(expected_block_time, op.get_time_now().get_real_secs())


    def test_sob_bursts_with_tx_time (self):
        '''
        The packet length field is not defined

        We input a packet len tag that occurs on the first sample of the block.

        We include a tx_time tag

        Check that one message is generated including all input samples
        and appropriate timestamp
        '''

        print("starting test_sob_bursts_with_tx_time")

        # put in a known (and easy to do math on) start time to make testing doable
        start_time_int_s = 100
        start_time_frac_s = 0.0

        tag_start_time_int_s = 200
        tag_start_time_frac_s = 0.5

        sink_inputs = dict(self.default_inputs)
        sink_inputs["tx_pkt_len_name"] = ""

        sample_rate = sink_inputs["sample_rate"]

        src_data = [0 + 1j, 2 + 3j, 4 +5j, 6 + 7j,
                    8 + 9j, 10 + 11j, 12 +13j, 14 + 15j, 16 + 17j, 18 + 19j]

        tag_offset = 0

        src_tags = [{"offset":tag_offset,
                     "key":self.tx_sob_name,
                     "value":True},
                     {"offset":tag_offset,
                     "key":self.tx_time_name,
                     "value":(tag_start_time_int_s, tag_start_time_frac_s)}]

        # convert src_tags into proper gnuradio stream tags
        src_tags = [dict_to_tag(st) for st in src_tags]

        # Note that currently the timestamp for envsim is in units of integer seconds and integer picoseconds
        expected_list = [
            {
                "meta":{
                    "timestamp_s":(tag_start_time_int_s,int(tag_start_time_frac_s*1e12)),
                    "packet_len":len(src_data)
                },
                "data":src_data
            },
        ]

        expected_block_time = tag_start_time_int_s + tag_start_time_frac_s + len(src_data)/sample_rate

        src = blocks.vector_source_c(src_data, False, 1, src_tags)

        print("length of source data vector: {}".format(len(src_data)))

        op = envsim.env_sink(**sink_inputs)

        # set start time instead of getting from system clock
        op.set_time_now(time_spec_t(start_time_int_s, start_time_frac_s))

        # connect up input and message destination blocks
        self.tb.connect(src, op)
        self.tb.msg_connect((op, 'event'), (self.msg_dst, 'store'))

        self.tb.run ()
        # check data

        result_list = [iq_packet_to_dict(self.msg_dst.get_message(i)) for i in range(self.msg_dst.num_messages())]

        self.assertPacketListEqual(expected_list, result_list)
        self.assertAlmostEqual(expected_block_time, op.get_time_now().get_real_secs())



if __name__ == '__main__':
    gr_unittest.run(qa_env_sink)
