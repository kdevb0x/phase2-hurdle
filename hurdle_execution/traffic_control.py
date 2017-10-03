#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import time

import pylxd

NUM_BOT_CONTAINERS = 3
NUM_COMPETITOR_CONTAINERS = 3
CONTAINER_NAME_PATTERN="competitor-hurdle-srn"

TGEN_SUBNET_BASE = 101
TGEN_PORT_BASE = 5001
TGEN_IP_PATTERN = "192.168.{}.2"

MGEN_MIN_MSG_SIZE = 28
MGEN_MAX_MSG_SIZE = 8192

MGEN_LOG_DIR = "/root/"
MGEN_SCRIPT_PATH = "/home/mgen/mgen_traffic.mgn"


def generate_simple_flows(tgen_names, num_bots, bot_msg_size, bot_msg_rate, num_comps, comp_msg_size, comp_msg_rate):
    '''
    generate a list of flows based on the number of bots and competitor nodes
    '''
    bot_tgen_ips = [TGEN_IP_PATTERN.format(TGEN_SUBNET_BASE + i) for i in range(num_bots)]
    bot_tgen_ports = [TGEN_PORT_BASE + i for i in range(num_bots)]

    # competitor IPs and port numbers start after those assigned to the bots
    comp_tgen_ips = [TGEN_IP_PATTERN.format(TGEN_SUBNET_BASE + i) for i in range(num_bots, num_bots+num_comps)]
    comp_tgen_ports = [TGEN_PORT_BASE + i for i in range(num_bots, num_bots+num_comps)]

    # build up flows for bots. Each bot talks to every other bot.
    bot_flows = {}
    for i in range(num_bots):
        bot_flows[i] = {"flows":[], "tgen_name":tgen_names[i]}

        # add a flow for each neighbor bot
        for j, (ip, port) in enumerate(zip(bot_tgen_ips, bot_tgen_ports)):
            # don't add flows to self
            if i != j:
                # send from a unique source port based on the DESTINATION node.
                # use a destination port based on the SOURCE node number
                bot_flows[i]["flows"].append({"src_port":bot_tgen_ports[j],
                                              "dst_ip":bot_tgen_ips[j],
                                              "dst_port":bot_tgen_ports[i],
                                              "msg_rate":bot_msg_rate,
                                              "msg_size":bot_msg_size,
                                              })

    # build up flows for competitor nodes. Each competitor node talks to every other competitor node.
    comp_flows = {}
    for i in range(num_comps):
        comp_flows[i] = {"flows":[], "tgen_name":tgen_names[i+num_bots]}

        # add a flow for each neighbor bot
        for j, (ip, port) in enumerate(zip(comp_tgen_ips, comp_tgen_ports)):
            # don't add flows to self
            if i != j:
                # send from a unique source port based on the DESTINATION node.
                # use a destination port based on the SOURCE node number
                comp_flows[i]["flows"].append({"src_port":comp_tgen_ports[j],
                                               "dst_ip":comp_tgen_ips[j],
                                               "dst_port":comp_tgen_ports[i],
                                               "msg_rate":comp_msg_rate,
                                               "msg_size":comp_msg_size,
                                              })

    return bot_flows, comp_flows


def write_leaky_udp_bucket_script(file_handle, flows, duration, listen_ports):

    for i, flow in enumerate(flows):
            # build up dict for passing in args by keyword to mgen script line writer
            mgen_args = {"flow_num":i+1, # seems to be 1 based according to online example scripts
                         "src_port":flow["src_port"],
                         "dst_ip":flow["dst_ip"],
                         "dst_port":flow["dst_port"],
                         "msg_rate":flow["msg_rate"],
                         "msg_size":flow["msg_size"]}

            # write the MGEN line for this flow
            file_handle.write("0.0 ON {flow_num} UDP SRC {src_port} DST {dst_ip}/{dst_port} PERIODIC [{msg_rate} {msg_size}]\n".format(**mgen_args))

    file_handle.write("\n# Tell flows when to stop\n")
    for i, flow in enumerate(flows):

        # write the MGEN line for this flow
        file_handle.write("{} OFF {}\n".format(duration, i+1)) # seems to be 1 based according to online example scripts


    file_handle.write("\n# Set up listen ports\n")
    listen_ports_str = ",".join([str(port) for port in listen_ports])
    file_handle.write("0.0 LISTEN UDP {}\n".format(listen_ports_str))

def write_mgen_script(file_name, traffic_profile, flows, listen_ports, duration):
    '''
    This writes common header and footer lines but calls traffic profile specific functions to
    set up flows
    '''
    with open(file_name, "w") as f:
        f.write("# MGEN SCRIPT {}\n".format(file_name))
        if traffic_profile == "leaky-udp-bucket":
            write_leaky_udp_bucket_script(file_handle=f,
                                          flows=flows,
                                          duration=duration,
                                          listen_ports=listen_ports)




def write_mgen_scripts(tgen_names, traffic_profile, num_bots, bot_msg_size, bot_msg_rate,
                       num_comps, comp_msg_size, comp_msg_rate, duration):
    '''
    this writes all the mgen scripts as temp files and returns a dictionary of script path indexed
    by intended traffic generator name.

    assumes tgen_names are ordered bots first
    '''

    mgen_scripts_by_tgen_node = {}

    if traffic_profile == 'leaky-udp-bucket':

        bot_flows, comp_flows = generate_simple_flows(tgen_names=tgen_names,
                                                      num_bots=num_bots,
                                                      bot_msg_size=bot_msg_size,
                                                      bot_msg_rate=bot_msg_rate,
                                                      num_comps=num_comps,
                                                      comp_msg_size=comp_msg_size,
                                                      comp_msg_rate=comp_msg_rate)

        bot_listen_ports = [TGEN_PORT_BASE + i for i in range(num_bots) ]
        comp_listen_ports = [TGEN_PORT_BASE + i for i in range(num_bots, num_bots+num_comps) ]

    # generate mgen scripts for all bots and store mapping between traffic generator name and file
    # path
    for bot_num, flow_dict in bot_flows.items():

        file_name = flow_dict["tgen_name"] + "_traffic.mgn"
        write_mgen_script(file_name=file_name,
                          traffic_profile=traffic_profile,
                          flows=flow_dict["flows"],
                          listen_ports=bot_listen_ports,
                          duration=duration)

        # store which script goes to what tgen node
        mgen_scripts_by_tgen_node[flow_dict["tgen_name"]] = file_name

    # generate mgen scripts for all competitor nodes and store mapping between traffic generator
    # name and file path
    for comp_num, flow_dict in comp_flows.items():

        file_name = flow_dict["tgen_name"] + "_traffic.mgn"
        write_mgen_script(file_name=file_name,
                          traffic_profile=traffic_profile,
                          flows=flow_dict["flows"],
                          listen_ports=comp_listen_ports,
                          duration=duration)

        # store which script goes to what tgen node
        mgen_scripts_by_tgen_node[flow_dict["tgen_name"]] = file_name



    return mgen_scripts_by_tgen_node

class Range(argparse.Action):
    '''
    Cleaner way of setting a large integer range of allowed vals
    '''
    def __init__(self, min=None, max=None, *args, **kwargs):
        self.min = min
        self.max = max
        kwargs["metavar"] = "[%d-%d]" % (self.min, self.max)
        super(Range, self).__init__(*args, **kwargs)

    def __call__(self, parser, namespace, value, option_string=None):
        if not (self.min <= value <= self.max):
            msg = 'invalid choice: %r (choose from [%d-%d])' % \
                (value, self.min, self.max)
            raise argparse.ArgumentError(self, msg)
        setattr(namespace, self.dest, value)


def main():

    # set up command line args
    parser = argparse.ArgumentParser(prog="traffic_control",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--tgen-container-name-base', default="tgen", dest="tgen_base",
                        help="Traffic generator container name prefix, no container number")

    parser.add_argument('--num-bot-nodes', default=3, type=int, dest="num_bots",
                        help="Number of bot nodes")

    parser.add_argument('--num-competitor-nodes', default=3, type=int, dest="num_comps",
                        help="Number of competitor nodes")

    subparsers = parser.add_subparsers(dest='action')

    # subparser for "stop" action. No args required, but doing it this way to make the commands
    # feel less wonky on the CLI
    parser_stop = subparsers.add_parser('stop',
                                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # subparser for "start" action.
    parser_start = subparsers.add_parser('start',
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser_start.add_argument('--traffic-profile', default="leaky-udp-bucket",
                              choices=["leaky-udp-bucket"],
                              help="Which traffic profile to use")

    parser_start.add_argument('--comp-msg-size', type=int, default=200,
                              min=MGEN_MIN_MSG_SIZE, max=MGEN_MAX_MSG_SIZE,
                              action=Range,
                              help="Message size in bytes for competitor nodes [%(min)d-%(max)d]")
    parser_start.add_argument('--comp-peak-msg-rate', type=float, default=10.0,
                              help="Peak message rate per link for competitor nodes, in messages per second")

    parser_start.add_argument('--bot-msg-size', type=int, default=200,
                              min=MGEN_MIN_MSG_SIZE, max=MGEN_MAX_MSG_SIZE,
                              action=Range,
                              help="Message size in bytes for bot nodes [%(min)d-%(max)d]")
    parser_start.add_argument('--bot-peak-msg-rate', type=float, default=10.0,
                              help="Peak message rate per link for bot nodes, in messages per second")

    parser_start.add_argument('--traffic-duration', type=float, default=300.0,
                            help="How long to run traffic profile, in seconds")


    # parse args and store to dictionary
    args = vars(parser.parse_args())

    # initialize lxd_client
    lxd_client = pylxd.Client()

    # get total number of traffic generators and list of names for traffic gens dedicated to
    # bots vs competitors
    num_tgens = args["num_comps"] + args["num_bots"]
    tgen_names = ["{}{}".format(args["tgen_base"], i) for i in range(1,num_tgens+1)]

    # split out names by whether they are dedicated to bots or competitor nodes
    bot_tgen_names = tgen_names[:args["num_bots"]]
    comp_tgen_names = tgen_names[args["num_bots"]:]

    # get reference to each container
    bot_tgens = []
    comp_tgens = []
    try:
        for cont_name in bot_tgen_names:
            bot_tgens.append(lxd_client.containers.get(cont_name))

        for cont_name in comp_tgen_names:
            comp_tgens.append(lxd_client.containers.get(cont_name))

    except pylxd.exceptions.NotFound as err:
        print("Could not find container name {}. Check 'lxc list' and if no containers are shown, re-run the hurdle initialization script".format(cont_name))

    # if action is "stop", stop each instance and exit
    if args["action"] == "stop":
        print("stopping MGEN flows and services")
        for cont in bot_tgens + comp_tgens:
            # check if service is running
            (ret_code, cmd_stdout, cmd_stderr) = cont.execute(["systemctl", "is-active", "mgen.service"])
            #print("systemd says mgen state is {}".format(cmd_stdout))
            if ret_code == 0:
                # service is running so shut it down
                print("Stopping MGEN service")
                exec_cmd = ["systemctl", "stop", "mgen"]
                print("running on {}: {}".format(cont.name, " ".join(exec_cmd)))
                cont.execute(exec_cmd)
            else:
                # service not running. Do nothing
                print("MGEN service already stopped on {}".format(cont.name))


        # we're done. Return.
        sys.exit(0)

    # if action is start:
    # given number of bots, number of competitor nodes, and per-link traffic load, generate mgen
    # script for each node
    file_map = write_mgen_scripts(tgen_names = tgen_names,
                                  traffic_profile = args["traffic_profile"],
                                  num_bots = args["num_bots"],
                                  bot_msg_size = args["bot_msg_size"],
                                  bot_msg_rate = args["bot_peak_msg_rate"],
                                  num_comps = args["num_comps"],
                                  comp_msg_size = args["comp_msg_size"],
                                  comp_msg_rate = args["comp_peak_msg_rate"],
                                  duration = args["traffic_duration"])


    # check if mgen is already running. If so, stop it
    for cont in bot_tgens + comp_tgens:
        # check if service is running
        (ret_code, cmd_stdout, cmd_stderr) = cont.execute(["systemctl", "is-active", "mgen.service"])
        #print("systemd says mgen state is {}".format(cmd_stdout))
        if ret_code == 0:
            # service already running. stop to ensure clean state.
            print("Stopping running MGEN service")
            exec_cmd = ["systemctl", "stop", "mgen"]
            print("running on {}: {}".format(cont.name, " ".join(exec_cmd)))
            cont.execute(exec_cmd)

    # copy scripts to appropriate nodes
    for tgen_name, source_file in file_map.items():

        push_cmd = ["lxc", "file", "push", source_file, tgen_name+MGEN_SCRIPT_PATH]
        print("Deploying MGEN script {} to {}".format(source_file, tgen_name+MGEN_SCRIPT_PATH))
        print("running {}".format(" ".join(push_cmd)))
        subprocess.run(push_cmd)

    # now start mgen
    for cont in bot_tgens + comp_tgens:

        # start mgen instance on MGEN service and start new log file
        exec_cmd = ["systemctl", "start", "mgen"]
        print("running on {}: {}".format(cont.name, " ".join(exec_cmd)))
        cont.execute(exec_cmd)

    # exit this script
    sys.exit(0)

if __name__ == "__main__":
    main()
