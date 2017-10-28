import copy
from datetime import datetime, timedelta

import json

import logging
logger = logging.getLogger(__name__)




def process_log(traffic_log):
    """
    Process a traffic log into a dictionary indexed by source IP with structure:

    {"X.X.X.X":{1:200,
                2:200,
                ...
                },
     "X.X.X.Y":{1:200,
                2:200,
                ...
                }
    }
    Top level keys are source IP addresses.
    Inner keys are sequence numbers and values are the packet sizes
    """

    # indexed by source IP
    scoring_log = {}

    all_ip_dsts = set()

    for mgen_entry in traffic_log:
        ip_dst = mgen_entry["ip_dst"].split("/")[0]

        # keep track of destination IPs. There should be only one.
        all_ip_dsts.add(ip_dst)

        ip_src = mgen_entry["ip_src"].split("/")[0]

        if ip_src not in scoring_log:
            scoring_log[ip_src] = {}

        # store off packet size by sequence number to prevent double counting
        scoring_log[ip_src][mgen_entry["seq_num"]] = mgen_entry["size"]

    if len(all_ip_dsts) > 1:
        logger.warn("Found more than one destination IP: %s. MGEN logs may be corrupt",
                    all_ip_dsts)

    # grab (what should be the only) IP from all_ip_dsts
    if len(all_ip_dsts) > 0:
        ip_dst = all_ip_dsts.pop()
    else:
         ip_dst = None

    return ip_dst, scoring_log

def score_traffic(bot_traffic_logs, competitor_traffic_logs, num_packets, json_log_name):
    """
    accepts two lists of dictionaries.

    Each is a list of traffic log dictionaries of the format:

    [{"time_recv":time_recv,
                  "time_sent":time_sent,
                  "flowid":flow_id,
                  "seq_num":seq_num,
                  "ip_src":ip_src,
                  "ip_dst":ip_dst,
                  "size":size},
                  ....
    ]


    This function will sort the mgen_logs of each dict by valid source
    and destination addresses and count the number of valid packets received.
    """

    bot_scoring = {}
    comp_scoring = {}

    total_score = {}

    for traffic_log in bot_traffic_logs:
        # process each log and store results by destination address
        dst_ip, scoring_log = process_log(traffic_log)
        if dst_ip is not None:
            bot_scoring[dst_ip] = copy.deepcopy(scoring_log)

    for traffic_log in competitor_traffic_logs:
        # process each log and store results by destination address
        dst_ip, scoring_log = process_log(traffic_log)
        if dst_ip is not None:
            comp_scoring[dst_ip] = copy.deepcopy(scoring_log)

    # now compute score
    total_bot_packets = 0
    total_score["bots"] = {}
    for dst_ip, scoring_log in bot_scoring.items():
        total_score["bots"][dst_ip] = {"packets_by_source":{}}
        for src_ip, pkt_dict in scoring_log.items():

            num_packets_received = len(pkt_dict)
            logger.info("Bot at IP: %s received %i packets from %s",
                        dst_ip, num_packets_received, src_ip)

            total_score["bots"][dst_ip]["packets_by_source"][src_ip] = num_packets_received
            total_bot_packets += num_packets_received

    total_score["bots"]["total"] = total_bot_packets

    # now compute score for competitors
    total_comp_packets = 0
    total_score["competitors"] = {}
    for dst_ip, scoring_log in comp_scoring.items():
        total_score["competitors"][dst_ip] = {"packets_by_source":{}}
        for src_ip, pkt_dict in scoring_log.items():

            num_packets_received = len(pkt_dict)
            logger.info("Competitor at IP: %s received %i packets from %s",
                        dst_ip, num_packets_received, src_ip)

            total_score["competitors"][dst_ip]["packets_by_source"][src_ip] = num_packets_received
            total_comp_packets += num_packets_received

    total_score["competitors"]["total"] = total_comp_packets

    logger.info("Bot network transfered a total of %i packets out of %i",
                total_bot_packets, num_packets)
    logger.info("Competitor network transfered a total of %i packets out of %i",
                total_comp_packets, num_packets)


    # save results to file
    with open(json_log_name, "w") as f:
        json.dump(total_score, f)
