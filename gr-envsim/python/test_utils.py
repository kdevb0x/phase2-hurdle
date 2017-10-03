'''
Misc utilities used in unit tests
'''

from itertools import izip
from gnuradio import gr_unittest
from gnuradio import gr
from gnuradio.gr import tag_t

import pmt

class Unbuffered(object):
    '''
    Make print statements output immediately, can be handy when looking
    through unit test outputs
    '''
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def writelines(self, datas):
        self.stream.writelines(datas)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)


def tag_to_dict(tag):
    '''
    Convert gnuradio stream tag to dict
    '''
    d = {"offset":tag.offset,
         "key":pmt.symbol_to_string(tag.key),
         "value":pmt.to_python(tag.value)
        }

    if not pmt.is_null(tag.srcid):
        d["srcid"] = pmt.to_python(tag.srcid)

    return d

def dict_to_tag(d):
    '''
    Convert dictionary to gnuadio stream tag
    '''
    tag = gr.tag_t()

    tag.offset = d["offset"]
    tag.key = pmt.to_pmt(d["key"])
    tag.value = pmt.to_pmt(d["value"])

    if "srcid" in d:
        tag.srcid = pmt.to_pmt(d["srcid"])

    return tag

def dict_to_iq_packet(d):
    '''
    dict is expected to be formatted as:
    {
        "meta":{
            "timestamp_counts":counts,
            "timestamp_s":(int_s, int_ps),
            "packet_len":num samples in packet
        }
        "data":[complex samples]
    }

    Returns a pmt type formatted according to how envsim_source
    expects it
    '''

    meta = pmt.to_pmt(d["meta"])
    data = pmt.init_c32vector(len(d["data"]), d["data"])

    return pmt.cons(meta, data)

def iq_packet_to_dict(pkt):
    '''
    convert an iq packet in pmt format back to a dictionary
    '''

    d = {
        "meta":pmt.to_python(pmt.car(pkt)),
        "data":pmt.to_python(pmt.cdr(pkt))
    }

    return d


class EnvSimAssertions(gr_unittest.TestCase):

    def assertPacketListEqual(self, e1_list, e2_list):

        self.assertEqual(len(e1_list), len(e2_list))

        for e1, e2 in izip(e1_list, e2_list):
            self.assertPacketEqual(e1,e2)


    def assertPacketEqual(self, e1, e2):
        '''
        test two events for equality
        '''

        # print("e1: {}".format(e1))
        # print("e2: {}".format(e2))

        # check event type
        self.assertDictEqual(e1["meta"], e2["meta"])

        # check vector
        self.assertSequenceEqual(list(e1["data"]), list(e2["data"]))


        # check for extra keys
        self.assertSetEqual(set(e1.keys()), set(e2.keys()))