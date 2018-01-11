import json
import unittest


from constants import RESULT_FILENAME
from constants import PACKET_SUCCESS_THRESHOLD

class TrafficTest(unittest.TestCase):

    # @unittest.expectedFailure
    # def test_bot_and_competitor_traffic(self):
    #     '''
    #     Test whether both competitor and bot networks passed the minimum amount of traffic
    #     '''

    #     with open(RESULT_FILENAME, "r") as f:
    #         total_score = json.load(f)

    #     # compute packet success threshold for both bot and competitor networks
    #     num_packets = float(total_score["input_packets_per_network"])
    #     total_bot_packets = float(total_score["bots"]["total"])
    #     total_comp_packets = float(total_score["competitors"]["total"])

    #     bot_packet_success_rate = total_bot_packets/num_packets
    #     comp_packet_success_rate = total_comp_packets/num_packets

    #     # assert that both bot and competitor networks passed our threshold
    #     bot_err_msg = "Bot FAIL: Required packet success rate: {} actual rate: {}".format(PACKET_SUCCESS_THRESHOLD,
    #                                                                                       bot_packet_success_rate)
    #     comp_err_msg = "Comp FAIL: Required packet success rate: {} actual rate: {}".format(PACKET_SUCCESS_THRESHOLD,
    #                                                                                         comp_packet_success_rate)
    #     self.assertGreaterEqual(bot_packet_success_rate, PACKET_SUCCESS_THRESHOLD, msg=bot_err_msg)

    #     self.assertGreaterEqual(comp_packet_success_rate, PACKET_SUCCESS_THRESHOLD, msg=comp_err_msg)

    def test_bot_traffic(self):
        '''
        Test whether bot network passed the minimum amount of traffic
        '''

        with open(RESULT_FILENAME, "r") as f:
            total_score = json.load(f)

        # compute packet success threshold for bot network
        num_packets = float(total_score["input_packets_per_network"])
        total_bot_packets = float(total_score["bots"]["total"])

        bot_packet_success_rate = total_bot_packets/num_packets

        # assert that bot network passed our threshold
        bot_err_msg = "Bot FAIL: Required packet success rate: {} actual rate: {}".format(PACKET_SUCCESS_THRESHOLD,
                                                                                          bot_packet_success_rate)

        self.assertGreaterEqual(bot_packet_success_rate, PACKET_SUCCESS_THRESHOLD, msg=bot_err_msg)