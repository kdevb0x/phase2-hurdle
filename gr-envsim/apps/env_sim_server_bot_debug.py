#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Env Sim Server Bot Debug
# Generated: Thu Oct 26 20:09:30 2017
##################################################

from gnuradio import analog
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio import zeromq
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser
import ConfigParser
import envsim
import temp_py_mod  # embedded python module
import time


class env_sim_server_bot_debug(gr.top_block):

    def __init__(self, config_file='envsim.ini'):
        gr.top_block.__init__(self, "Env Sim Server Bot Debug")

        ##################################################
        # Parameters
        ##################################################
        self.config_file = config_file

        ##################################################
        # Variables
        ##################################################
        self._usrp_ip_prefix_str_config = ConfigParser.ConfigParser()
        self._usrp_ip_prefix_str_config.read(config_file)
        try: usrp_ip_prefix_str = self._usrp_ip_prefix_str_config.get('main', 'usrp_ip_prefix')
        except: usrp_ip_prefix_str = '192.168.40.'
        self.usrp_ip_prefix_str = usrp_ip_prefix_str
        self._usrp_ip_base_config = ConfigParser.ConfigParser()
        self._usrp_ip_base_config.read(config_file)
        try: usrp_ip_base = self._usrp_ip_base_config.getint('main', 'usrp_ip_base')
        except: usrp_ip_base = 101
        self.usrp_ip_base = usrp_ip_base
        self.num_nodes = num_nodes = 3
        self.now = now = time.time()
        self._increment_usrp_address_bool_config = ConfigParser.ConfigParser()
        self._increment_usrp_address_bool_config.read(config_file)
        try: increment_usrp_address_bool = self._increment_usrp_address_bool_config.getboolean('main', 'increment_usrp_address')
        except: increment_usrp_address_bool = True
        self.increment_usrp_address_bool = increment_usrp_address_bool
        self.zmq_base_addr = zmq_base_addr = "tcp://10.169.25.150:"
        self.usrp_ip_list = usrp_ip_list = temp_py_mod.make_usrp_ip_list(increment_usrp_address_bool, usrp_ip_prefix_str, usrp_ip_base, num_nodes)
        self._samp_rate_config = ConfigParser.ConfigParser()
        self._samp_rate_config.read(config_file)
        try: samp_rate = self._samp_rate_config.getfloat('main', 'samp_rate')
        except: samp_rate = 2e6
        self.samp_rate = samp_rate
        self._port_num_base_config = ConfigParser.ConfigParser()
        self._port_num_base_config.read(config_file)
        try: port_num_base = self._port_num_base_config.getint('main', 'port_num_base')
        except: port_num_base = 52001
        self.port_num_base = port_num_base
        self._noise_amp_config = ConfigParser.ConfigParser()
        self._noise_amp_config.read(config_file)
        try: noise_amp = self._noise_amp_config.getfloat('main', 'noise_amp')
        except: noise_amp = .001
        self.noise_amp = noise_amp
        self._host_config = ConfigParser.ConfigParser()
        self._host_config.read(config_file)
        try: host = self._host_config.get('main', 'host_ip')
        except: host = '192.168.40.2'
        self.host = host
        self.env_time_int_s = env_time_int_s = int(now)
        self.env_time_frac_s = env_time_frac_s = now-int(now)
        self._channel_gain_linear_config = ConfigParser.ConfigParser()
        self._channel_gain_linear_config.read(config_file)
        try: channel_gain_linear = self._channel_gain_linear_config.getfloat('main', 'channel_gain_linear')
        except: channel_gain_linear = .01
        self.channel_gain_linear = channel_gain_linear

        ##################################################
        # Blocks
        ##################################################
        self.zeromq_push_sink_0_0_0_0 = zeromq.push_sink(gr.sizeof_gr_complex, 1, zmq_base_addr+str(port_num_base+3), 100, False, -1)
        self.envsim_zmq_envsim_source_0_1 = envsim.zmq_envsim_source("tcp://"+ usrp_ip_list[2]+ ":" +  str(port_num_base+2),
                                         10,
                                         100,
                                         samp_rate,
                                         env_time_int_s,
                                         env_time_frac_s)

        self.envsim_zmq_envsim_source_0_0 = envsim.zmq_envsim_source("tcp://"+ usrp_ip_list[1]+ ":" +  str(port_num_base+1),
                                         10,
                                         100,
                                         samp_rate,
                                         env_time_int_s,
                                         env_time_frac_s)

        self.envsim_zmq_envsim_source_0 = envsim.zmq_envsim_source("tcp://"+ usrp_ip_list[0] + ":" +  str(port_num_base+0),
                                         10,
                                         100,
                                         samp_rate,
                                         env_time_int_s,
                                         env_time_frac_s)

        self.envsim_socket_meta_pdu_0_2 = envsim.socket_meta_pdu("UDP_CLIENT", usrp_ip_list[0], str(port_num_base+0), 40000, False)
        self.envsim_socket_meta_pdu_0_1_3 = envsim.socket_meta_pdu("UDP_CLIENT", usrp_ip_list[2], str(port_num_base+2), 40000, False)
        self.envsim_socket_meta_pdu_0_0_0 = envsim.socket_meta_pdu("UDP_CLIENT", usrp_ip_list[1], str(port_num_base+1), 40000, False)
        self.blocks_throttle_0 = blocks.throttle(gr.sizeof_gr_complex*1, samp_rate,True)
        self.blocks_tagged_stream_to_pdu_0 = blocks.tagged_stream_to_pdu(blocks.complex_t, 'packet_len')
        self.blocks_stream_to_tagged_stream_0 = blocks.stream_to_tagged_stream(gr.sizeof_gr_complex, 1, 2048, "packet_len")
        self.blocks_probe_rate_0 = blocks.probe_rate(gr.sizeof_gr_complex*1, 5000.0, 0.15)
        self.blocks_multiply_const_xx_0 = blocks.multiply_const_cc(channel_gain_linear)
        self.blocks_message_debug_0 = blocks.message_debug()
        self.blocks_add_xx_0_0 = blocks.add_vcc(1)
        self.blocks_add_xx_0 = blocks.add_vcc(1)
        self.analog_noise_source_x_0 = analog.noise_source_c(analog.GR_GAUSSIAN, noise_amp, 0)

        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.blocks_probe_rate_0, 'rate'), (self.blocks_message_debug_0, 'print'))
        self.msg_connect((self.blocks_tagged_stream_to_pdu_0, 'pdus'), (self.envsim_socket_meta_pdu_0_0_0, 'pdus'))
        self.msg_connect((self.blocks_tagged_stream_to_pdu_0, 'pdus'), (self.envsim_socket_meta_pdu_0_1_3, 'pdus'))
        self.msg_connect((self.blocks_tagged_stream_to_pdu_0, 'pdus'), (self.envsim_socket_meta_pdu_0_2, 'pdus'))
        self.connect((self.analog_noise_source_x_0, 0), (self.blocks_add_xx_0_0, 1))
        self.connect((self.blocks_add_xx_0, 0), (self.blocks_multiply_const_xx_0, 0))
        self.connect((self.blocks_add_xx_0_0, 0), (self.blocks_throttle_0, 0))
        self.connect((self.blocks_multiply_const_xx_0, 0), (self.blocks_add_xx_0_0, 0))
        self.connect((self.blocks_stream_to_tagged_stream_0, 0), (self.blocks_tagged_stream_to_pdu_0, 0))
        self.connect((self.blocks_stream_to_tagged_stream_0, 0), (self.zeromq_push_sink_0_0_0_0, 0))
        self.connect((self.blocks_throttle_0, 0), (self.blocks_probe_rate_0, 0))
        self.connect((self.blocks_throttle_0, 0), (self.blocks_stream_to_tagged_stream_0, 0))
        self.connect((self.envsim_zmq_envsim_source_0, 0), (self.blocks_add_xx_0, 0))
        self.connect((self.envsim_zmq_envsim_source_0_0, 0), (self.blocks_add_xx_0, 1))
        self.connect((self.envsim_zmq_envsim_source_0_1, 0), (self.blocks_add_xx_0, 2))

    def get_config_file(self):
        return self.config_file

    def set_config_file(self, config_file):
        self.config_file = config_file
        self._samp_rate_config = ConfigParser.ConfigParser()
        self._samp_rate_config.read(self.config_file)
        if not self._samp_rate_config.has_section('main'):
        	self._samp_rate_config.add_section('main')
        self._samp_rate_config.set('main', 'samp_rate', str(None))
        self._samp_rate_config.write(open(self.config_file, 'w'))
        self._port_num_base_config = ConfigParser.ConfigParser()
        self._port_num_base_config.read(self.config_file)
        if not self._port_num_base_config.has_section('main'):
        	self._port_num_base_config.add_section('main')
        self._port_num_base_config.set('main', 'port_num_base', str(None))
        self._port_num_base_config.write(open(self.config_file, 'w'))
        self._noise_amp_config = ConfigParser.ConfigParser()
        self._noise_amp_config.read(self.config_file)
        if not self._noise_amp_config.has_section('main'):
        	self._noise_amp_config.add_section('main')
        self._noise_amp_config.set('main', 'noise_amp', str(None))
        self._noise_amp_config.write(open(self.config_file, 'w'))
        self._channel_gain_linear_config = ConfigParser.ConfigParser()
        self._channel_gain_linear_config.read(self.config_file)
        if not self._channel_gain_linear_config.has_section('main'):
        	self._channel_gain_linear_config.add_section('main')
        self._channel_gain_linear_config.set('main', 'channel_gain_linear', str(None))
        self._channel_gain_linear_config.write(open(self.config_file, 'w'))
        self._usrp_ip_prefix_str_config = ConfigParser.ConfigParser()
        self._usrp_ip_prefix_str_config.read(self.config_file)
        if not self._usrp_ip_prefix_str_config.has_section('main'):
        	self._usrp_ip_prefix_str_config.add_section('main')
        self._usrp_ip_prefix_str_config.set('main', 'usrp_ip_prefix', str(None))
        self._usrp_ip_prefix_str_config.write(open(self.config_file, 'w'))
        self._usrp_ip_base_config = ConfigParser.ConfigParser()
        self._usrp_ip_base_config.read(self.config_file)
        if not self._usrp_ip_base_config.has_section('main'):
        	self._usrp_ip_base_config.add_section('main')
        self._usrp_ip_base_config.set('main', 'usrp_ip_base', str(None))
        self._usrp_ip_base_config.write(open(self.config_file, 'w'))
        self._increment_usrp_address_bool_config = ConfigParser.ConfigParser()
        self._increment_usrp_address_bool_config.read(self.config_file)
        if not self._increment_usrp_address_bool_config.has_section('main'):
        	self._increment_usrp_address_bool_config.add_section('main')
        self._increment_usrp_address_bool_config.set('main', 'increment_usrp_address', str(None))
        self._increment_usrp_address_bool_config.write(open(self.config_file, 'w'))
        self._host_config = ConfigParser.ConfigParser()
        self._host_config.read(self.config_file)
        if not self._host_config.has_section('main'):
        	self._host_config.add_section('main')
        self._host_config.set('main', 'host_ip', str(None))
        self._host_config.write(open(self.config_file, 'w'))

    def get_usrp_ip_prefix_str(self):
        return self.usrp_ip_prefix_str

    def set_usrp_ip_prefix_str(self, usrp_ip_prefix_str):
        self.usrp_ip_prefix_str = usrp_ip_prefix_str
        self.set_usrp_ip_list(temp_py_mod.make_usrp_ip_list(self.increment_usrp_address_bool, self.usrp_ip_prefix_str, self.usrp_ip_base, self.num_nodes))

    def get_usrp_ip_base(self):
        return self.usrp_ip_base

    def set_usrp_ip_base(self, usrp_ip_base):
        self.usrp_ip_base = usrp_ip_base
        self.set_usrp_ip_list(temp_py_mod.make_usrp_ip_list(self.increment_usrp_address_bool, self.usrp_ip_prefix_str, self.usrp_ip_base, self.num_nodes))

    def get_num_nodes(self):
        return self.num_nodes

    def set_num_nodes(self, num_nodes):
        self.num_nodes = num_nodes
        self.set_usrp_ip_list(temp_py_mod.make_usrp_ip_list(self.increment_usrp_address_bool, self.usrp_ip_prefix_str, self.usrp_ip_base, self.num_nodes))

    def get_now(self):
        return self.now

    def set_now(self, now):
        self.now = now
        self.set_env_time_int_s(int(self.now))
        self.set_env_time_frac_s(self.now-int(self.now))

    def get_increment_usrp_address_bool(self):
        return self.increment_usrp_address_bool

    def set_increment_usrp_address_bool(self, increment_usrp_address_bool):
        self.increment_usrp_address_bool = increment_usrp_address_bool
        self.set_usrp_ip_list(temp_py_mod.make_usrp_ip_list(self.increment_usrp_address_bool, self.usrp_ip_prefix_str, self.usrp_ip_base, self.num_nodes))

    def get_zmq_base_addr(self):
        return self.zmq_base_addr

    def set_zmq_base_addr(self, zmq_base_addr):
        self.zmq_base_addr = zmq_base_addr

    def get_usrp_ip_list(self):
        return self.usrp_ip_list

    def set_usrp_ip_list(self, usrp_ip_list):
        self.usrp_ip_list = usrp_ip_list

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle_0.set_sample_rate(self.samp_rate)

    def get_port_num_base(self):
        return self.port_num_base

    def set_port_num_base(self, port_num_base):
        self.port_num_base = port_num_base

    def get_noise_amp(self):
        return self.noise_amp

    def set_noise_amp(self, noise_amp):
        self.noise_amp = noise_amp
        self.analog_noise_source_x_0.set_amplitude(self.noise_amp)

    def get_host(self):
        return self.host

    def set_host(self, host):
        self.host = host

    def get_env_time_int_s(self):
        return self.env_time_int_s

    def set_env_time_int_s(self, env_time_int_s):
        self.env_time_int_s = env_time_int_s

    def get_env_time_frac_s(self):
        return self.env_time_frac_s

    def set_env_time_frac_s(self, env_time_frac_s):
        self.env_time_frac_s = env_time_frac_s

    def get_channel_gain_linear(self):
        return self.channel_gain_linear

    def set_channel_gain_linear(self, channel_gain_linear):
        self.channel_gain_linear = channel_gain_linear
        self.blocks_multiply_const_xx_0.set_k(self.channel_gain_linear)


def argument_parser():
    parser = OptionParser(usage="%prog: [options]", option_class=eng_option)
    parser.add_option(
        "", "--config-file", dest="config_file", type="string", default='envsim.ini',
        help="Set config_file [default=%default]")
    return parser


def main(top_block_cls=env_sim_server_bot_debug, options=None):
    if options is None:
        options, _ = argument_parser().parse_args()

    tb = top_block_cls(config_file=options.config_file)
    tb.start()
    tb.wait()


if __name__ == '__main__':
    main()
