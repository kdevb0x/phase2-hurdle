#!/usr/bin/env python3

import argparse
import configparser
import json
import logging
import math
import os
import pylxd
import subprocess
import sys
import time

from constants import RESULT_FILENAME

from mgen_parser import mgen_parser
from traffic_scoring import score_traffic


# note this is used in a couple of files. pull out to config file
COMPETITOR_NAME_BASE='competitor-hurdle-srn'
NUM_COMPETITOR_CONTAINERS = 3
NUM_BOT_CONTAINERS = 3

CONTAINER_BOOT_TIMEOUT=300.0
COMMAND_PATH_BASE="./"

ENVSIM_PORT_NUM_BASE=52001
ENVSIM_CONFIG_PATH = "/root/phase2-hurdle/gr-envsim/apps/envsim.ini"



# USRP Interfaces start at 192.168.40.<USRP0_IP_BASE + node num (0 indexed)>
USRP_IP_PREFIX = "192.168.40."
USRP_IP_BASE = 101
ENVSIM_IP = "192.168.40.2"

# TODO: This is currently hardcoded in collab_server.service. Update collab server to use
# config files and pull these params from there
COLLAB_SERVER_IP = "172.30.101.1"
COLLAB_SERVER_PORT = 5556
COLLAB_CLIENT_PORT = 5557
COLLAB_PEER_PORT = 5558

# allow an extra 10 seconds for traffic to spool up and shut down
HURDLE_TIMING_SLOP = 10.0

RADIO_API_PATH = "/root/radio_api"
BOT_STATE_FILE_PATH = "/var/log/bot_state"

TGEN_NAME_BASE = "tgen"
MGEN_LOG_PATH = "/home/mgen/mgen_traffic_log.drc"

FORMAT = '%(asctime)s %(name)s %(levelname)s: %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)
logger = logging.getLogger(__name__)

# ws4py is way too chatty by default.
ws4pylogger = logging.getLogger("ws4py")
ws4pylogger.setLevel(logging.WARN)

def retrieve_traffic_logs(bot_names, comp_names, tgen_name_base):
    '''
    pull traffic logs out of tgen containers
    '''

    name_list = bot_names + comp_names
    bot_logfiles = []
    comp_logfiles = []

    for i, name in enumerate(bot_names):
        tgen_name = tgen_name_base + "{}".format(i+1)

        source = tgen_name+MGEN_LOG_PATH
        destination = "./{}_mgen_traffic_log.drc".format(name)

        bot_logfiles.append(destination)

        push_cmd = ["lxc", "file", "pull", source, destination]
        print("Pulling traffic log file from {} to {}".format(source, destination))
        print("running {}".format(" ".join(push_cmd)))
        subprocess.run(push_cmd)

    for i, name in enumerate(comp_names):
        tgen_name = tgen_name_base + "{}".format(i+1+len(bot_names))

        source = tgen_name+MGEN_LOG_PATH
        destination = "./{}_mgen_traffic_log.drc".format(name)

        comp_logfiles.append(destination)

        push_cmd = ["lxc", "file", "pull", source, destination]
        print("Pulling traffic log file from {} to {}".format(source, destination))
        print("running {}".format(" ".join(push_cmd)))
        subprocess.run(push_cmd)

    return bot_logfiles, comp_logfiles

def handle_collab_server(action):
    '''
    Start or stop the collab server.
    Action is stop, start, or restart
    '''

    #TODO: Add some error checking/handling here

    # start mgen instance on MGEN service and start new log file
    exec_cmd = ["systemctl", action, "collab_server"]
    print("running {}".format(" ".join(exec_cmd)))
    subprocess.run(exec_cmd)



def write_colosseum_config_ini_files(num_nodes, envsim_port_base, collab_server_ip,
                                     collab_server_port, collab_client_port, collab_peer_port,
                                     samp_rate, center_freq=1e9):
    '''
    Write out num_nodes unique colosseum_config files and return a list of filenames
    '''

    # first build up ini file contents
    config = configparser.ConfigParser()
    config['RF'] = {"center_frequency":center_freq,
                    "rf_bandwidth":samp_rate}

    config['COLLABORATION'] = {"collab_server_ip":collab_server_ip,
                               "collab_server_port":collab_server_port,
                               "collab_client_port":collab_client_port,
                               "collab_peer_port":collab_peer_port}

    config_filenames = []

    for i in range(num_nodes):
        # Add port numbers for envsim
        config["ENVSIM"] = {"envsim_port":envsim_port_base+i,
                            "envsim_ip":ENVSIM_IP}

        # write out colosseum config file for each node
        config_filename = "node_{}_colosseum_config.ini".format(i+1)
        with open(config_filename, 'w') as configfile:
            config.write(configfile)

        config_filenames.append(config_filename)

    return config_filenames

def install_colosseum_config_files(bot_containers, comp_containers, config_filenames):
    '''
    push a colosseum config file into /root/radio_api for each node
    '''
    container_list = bot_containers + comp_containers

    for container, config_file in zip(container_list, config_filenames):

        destination = container.name+os.path.join(RADIO_API_PATH, "colosseum_config.ini")

        push_cmd = ["lxc", "file", "push", config_file, destination]
        print("Deploying Colosseum Config file {} to {}".format(config_file, destination))
        print("running {}".format(" ".join(push_cmd)))
        subprocess.run(push_cmd)

def poll_radio_api_for_start_with_timeout(bot_containers, comp_containers, boot_timeout):
    '''
    loop over bot and competitor containers until either all containers report they are
    ready or the timeout hits, whichever happens first
    '''
    boot_start_time = time.time()
    elapsed_time = time.time() - boot_start_time

    booting_containers = bot_containers + comp_containers

    status_cmd = [os.path.join(RADIO_API_PATH,"status.sh")]


    # loop until all containers have booted, or until the timeout hits, whichever happens first
    while(len(booting_containers) > 0 and elapsed_time<boot_timeout):

        # temp list to keep track of which containers still haven't booted to avoid
        # changing the booting_container list while we iterate over it
        containers_still_booting = []

        # check all the containers
        for c in booting_containers:
            container_ready = False

            print("Checking {} status by calling {}".format(c.name, status_cmd))
            (retcode, stdout, stderr) = c.execute(status_cmd)

            # remove whitespace to be a little forgiving
            result_json = stdout.strip()

            # try to parse the result
            try:
                result = json.loads(result_json)
                if (result["STATUS"] == "READY") or (result["STATUS"] == "ACTIVE"):
                    container_ready = True

                print("container {} reports status: {}".format(c.name, result["STATUS"]))

            except ValueError:
                print("Could not parse result as valid JSON: {}".format(result_json))

            except KeyError as err:
                print("Key 'STATUS' not found in JSON dict returned by container")
                print(err)

            if container_ready:
                print("Container {} has booted".format(c.name))
                pass
            else:
                containers_still_booting.append(c)

        # update conainer booting list
        booting_containers = containers_still_booting

        # sleep until next poll
        time.sleep(10.0)
        elapsed_time = time.time() - boot_start_time

        print("{} seconds left before timeout reached".format(int(boot_timeout-elapsed_time)))

        if elapsed_time > boot_timeout:
            print("Boot timeout expired after {} seconds. Continuing anyway.".format(elapsed_time))

def run_radio_api_on_nodes(container_list, script):
    '''
    Run the specified radio_api script on every container in the container list
    '''

    for c in reversed(container_list):
        print("calling {} on {}".format(script, c.name))
        try:
            (retcode, stdout, stderr) = c.execute([script,])
            print("return code: {}".format(retcode))
            print("stdout: {}".format(stdout))
            print("stderr: {}".format(stderr))

        except pylxd.exceptions.LXDAPIException as err:
            print("call threw error: {}".format(err))

def run_subproc_and_print_output(cmd):
    '''
    Call the subprocess using the given command list, print out the subproc stdout and
    stderr, and check the return code
    '''

    subproc = subprocess.run(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            universal_newlines=True)

    print(subproc.stdout)

    if subproc.returncode == 0:
        pass
    else:
        print("non-zero return code, proceed with caution")

    # just in case we want to do something more than print a warning
    return subproc.returncode

def cleanup_bots(bot_containers):
    '''
    clear the bot status file from /var/log/bot_state in each bot container
    '''
    for container in bot_containers:

        cleanup_cmd = ["lxc", "exec", container.name, "rm", BOT_STATE_FILE_PATH]
        print("running {}".format(" ".join(cleanup_cmd)))
        subprocess.run(cleanup_cmd)

def main():

    # set up command line args
    parser = argparse.ArgumentParser(prog="run_hurdle",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--bot-mode", choices=["practice", "scoring", "dummy"], default="practice",
                        help="Practice or Scoring mode")

    parser.add_argument('--duration', type=float, default=300.0,
                        help="How long to run hurdle, not including bootup, in seconds")

    parser.add_argument('--sample-rate', type=float, default=1e6, choices=[200e3, 500e3, 1e6, 2e6],
                        help="Sample rate to run the hurdle")

    parser.add_argument('--image-file', default="competitor-image.tar.gz",
                        help="Name of the container stored in /share/nas/competitor/images/ to use for this run")

    parser.add_argument('--disable-competitor-containers', action="store_true", default=False,
                        help="When specified, the run script will not use the competitor containers")

    parser.add_argument('--clean-competitor-containers', action="store_true", default=False,
                        help="When specified, this flag will make the run script remove the competitor containers at the end of a run")

    parser.add_argument('--packet-rate', type=float, default=15.0,
                        help="Packet rate for bots and competitors")

    parser.add_argument('--noise-amp', type=float, default=0.0001,
                        help="Amplitude of gaussian background noise")

    parser.add_argument('--chan-gain-linear', type=float, default=0.1,
                        help="Channel gain as a linear scalar applied to each channel")

    parser.add_argument('--enable-debug-output', action="store_true", default=False,
                        help="When specified, this flag will run the envsim with a ZMQ push socket that outputs the samples sent to competitor containers")


    # parse args and store to dictionary
    args = vars(parser.parse_args())

    # initialize pylxd client
    lxd_client = pylxd.Client()


    # set up whether we're using practice or scoring bot mode.
    if args["bot_mode"] == "practice":
        bot_name_base = "darpa-practice-srn"

    elif args["bot_mode"] == "scoring":
        bot_name_base = "darpa-scoring-srn"

    # used only for internal debug
    elif args["bot_mode"] == "dummy":
        bot_name_base = "dummy-tx-srn"
    else:
        raise ValueError("Uknown bot mode {} specified".format(args["bot_mode"]))

    if args["disable_competitor_containers"]:
        comp_containers = []
        comp_container_names = []
        # put envsim into a 3 channel mode instead of the full six channel mode
        envsim_mode = "bot-debug"
    else:
        # run envsim in its normal 6 channel mode
        envsim_mode = "hurdle"

        # initialize and configure 3 copies of competitor container
        cmd = [os.path.join(COMMAND_PATH_BASE, "configure_competitor_containers.py"),
            "--image-file", args["image_file"]]
        print("Initializing competitor containers based on {}. This may take several minutes".format(args["image_file"]))
        print("Running {}".format(" ".join(cmd)))
        ret_code = run_subproc_and_print_output(cmd)

        if ret_code != 0:
            print("Could not load competitor container. Exiting")
            sys.exit(1)

        comp_container_names = [COMPETITOR_NAME_BASE+"{}".format(i+1) for i in range(NUM_BOT_CONTAINERS, NUM_BOT_CONTAINERS+NUM_COMPETITOR_CONTAINERS)]

        # get references to competitor containers
        comp_containers = [lxd_client.containers.get(name) for name in comp_container_names]
        if len(comp_containers) != NUM_COMPETITOR_CONTAINERS:
            print("Expecting {} competitor containers, found {}".format(NUM_COMPETITOR_CONTAINERS, len(comp_containers)))
            if len(comp_containers) > NUM_COMPETITOR_CONTAINERS:
                print("Please remove extra containers with lxc rm <name>. Current list is: {}".format(comp_container_names))
            else:
                print("Competitor containers not found. List is: {}".format(my_containers))
            raise ValueError

    # get list of all containers currently loaded
    my_containers = lxd_client.containers.all()

    # build list of expected bot container names
    bot_container_names = [bot_name_base+"{}".format(i+1) for i in range(NUM_BOT_CONTAINERS)]

    # get references to bot containers
    bot_containers = [lxd_client.containers.get(name) for name in bot_container_names]
    if len(bot_containers) != NUM_BOT_CONTAINERS:
        print("Expecting {} bot containers, found {}".format(NUM_BOT_CONTAINERS, len(bot_containers)))
        if len(bot_containers) > NUM_BOT_CONTAINERS:
            print("Please remove extra containers with lxc rm <name>. Current list is: {}".format(bot_containers))
        else:
            print("Bot containers not found. List is: {}".format(my_containers))
            print("Consider removing all bot containers and re-running the hurdle container initialization script")
        raise ValueError


    # Set up and deploy Colosseum Config files to nodes
    config_filenames = write_colosseum_config_ini_files(num_nodes=len(comp_containers)+len(bot_containers),
                                                        envsim_port_base=ENVSIM_PORT_NUM_BASE,
                                                        collab_server_ip=COLLAB_SERVER_IP,
                                                        collab_server_port=COLLAB_SERVER_PORT,
                                                        collab_client_port=COLLAB_CLIENT_PORT,
                                                        collab_peer_port=COLLAB_PEER_PORT,
                                                        samp_rate=args["sample_rate"],
                                                        center_freq=1e9)

    # Push ColosseumConfig.ini into bot and competitor containers
    install_colosseum_config_files(bot_containers, comp_containers, config_filenames)

    # start all containers
    cmd = [os.path.join(COMMAND_PATH_BASE, "container_control.py"),
            "--bot-container-name-base={}".format(bot_name_base),
            "--competitor-container-name-base={}".format(COMPETITOR_NAME_BASE),
            "--tgen-container-name-base={}".format(TGEN_NAME_BASE),
            "start"]

    print("Starting containers by running {}".format(" ".join(cmd)))
    ret_code = run_subproc_and_print_output(cmd)

    if ret_code != 0:
        print("All necessary containers did not start. Exiting")
        sys.exit(1)



    # start envsim
    cmd = [os.path.join(COMMAND_PATH_BASE, "envsim_control.py"),
           "--mode={}".format(envsim_mode)]

    if args["enable_debug_output"]:
        cmd.append("--enable-debug-output")

    cmd.extend(["start",
                "--port-num-base={}".format(ENVSIM_PORT_NUM_BASE),
                "--samp-rate={}".format(args["sample_rate"]),
                "--usrp-ip-prefix={}".format(USRP_IP_PREFIX),
                "--usrp-ip-base={}".format(USRP_IP_BASE),
                "--channel-gain-linear={}".format(args["chan_gain_linear"]),
                "--noise-amp={}".format(args["noise_amp"]),
                "--envsim-config-file={}".format(ENVSIM_CONFIG_PATH)])

    print("Starting envsim by running {}".format(" ".join(cmd)))
    ret_code = run_subproc_and_print_output(cmd)

    if ret_code != 0:
        print("Environment simulator did not start. Exiting")
        sys.exit(1)

    # Start collaboration server
    handle_collab_server(action="start")

    # poll containers for ready state in radio_api loop
    poll_radio_api_for_start_with_timeout(bot_containers, comp_containers, CONTAINER_BOOT_TIMEOUT)

    print("all containers booted")

    # when all containers ready:
    # setup top level container routing
    cmd = [os.path.join(COMMAND_PATH_BASE, "traffic_routing_setup.sh")]
    print("Setting up routing by running {}".format(" ".join(cmd)))
    ret_code = run_subproc_and_print_output(cmd)

    if ret_code != 0:
        print("Routing table setup unsuccessful. Consider running traffic_routing_teardown.sh and trying again")
        sys.exit(1)

    #   call start on each node
    run_radio_api_on_nodes(bot_containers+comp_containers, script=os.path.join(RADIO_API_PATH,"start.sh"))

    #   start traffic
    cmd = [os.path.join(COMMAND_PATH_BASE, "traffic_control.py"),
           "start",
           "--traffic-duration", str(args["duration"]),
           "--bot-peak-msg-rate={}".format(args["packet_rate"]),
           "--comp-peak-msg-rate={}".format(args["packet_rate"])]

    print("Starting traffic by running {}".format(" ".join(cmd)))
    ret_code = run_subproc_and_print_output(cmd)

    #   wait around for traffic duration, periodically calling radio_api status
    start_time = time.time()
    elapsed_time = time.time()-start_time
    hurdle_time = args["duration"] + HURDLE_TIMING_SLOP
    while(elapsed_time < hurdle_time):
        print("waiting {} more seconds for hurdle to complete".format(hurdle_time-elapsed_time))
        run_radio_api_on_nodes(bot_containers+comp_containers, script=os.path.join(RADIO_API_PATH,"status.sh"))
        time.sleep(10)
        elapsed_time = time.time()-start_time



    # when time is up:
    #   stop traffic
    cmd = [os.path.join(COMMAND_PATH_BASE, "traffic_control.py"),
           "stop"]

    print("Stopping traffic by running {}".format(" ".join(cmd)))
    ret_code = run_subproc_and_print_output(cmd)

    #   teardown routing
    cmd = [os.path.join(COMMAND_PATH_BASE, "traffic_routing_teardown.sh")]
    print("Tearing down routing by running {}".format(" ".join(cmd)))
    ret_code = run_subproc_and_print_output(cmd)


    #   call stop on each node
    run_radio_api_on_nodes(bot_containers+comp_containers, script=os.path.join(RADIO_API_PATH,"stop.sh"))

    # stop collaboration server
    handle_collab_server(action="stop")

    #   stop envsim
    cmd = [os.path.join(COMMAND_PATH_BASE, "envsim_control.py"),
           "--mode={}".format(envsim_mode)]

    if args["enable_debug_output"]:
        cmd.append("--enable-debug-output")

    cmd.append("stop")

    print("Stopping envsim by running {}".format(" ".join(cmd)))
    ret_code = run_subproc_and_print_output(cmd)

    # remove status files from bots so they boot cleanly next run
    cleanup_bots(bot_containers)

    #   stop all containers
    cmd = [os.path.join(COMMAND_PATH_BASE, "container_control.py"),
           "--bot-container-name-base={}".format(bot_name_base),
           "--competitor-container-name-base={}".format(COMPETITOR_NAME_BASE),
           "--tgen-container-name-base={}".format(TGEN_NAME_BASE),
           "stop"]
    print("Stopping containers by running {}".format(" ".join(cmd)))
    ret_code = run_subproc_and_print_output(cmd)


    #   TODO: consider what other logs we should grab
    bot_logfiles, comp_logfiles = retrieve_traffic_logs(bot_container_names,
                                                        comp_container_names,
                                                        TGEN_NAME_BASE)

    # parse bot and competitor log files
    bot_traffic_logs = [mgen_parser(bot_log) for bot_log in bot_logfiles]
    comp_traffic_logs = [mgen_parser(comp_log) for comp_log in comp_logfiles]

    # compute expected number of packets per network
    bootup_slop_time = 8.0
    num_packets = math.floor(args["packet_rate"]*NUM_BOT_CONTAINERS*(args["duration"]-bootup_slop_time)*(NUM_BOT_CONTAINERS-1))
    score_traffic(bot_traffic_logs, comp_traffic_logs, num_packets, RESULT_FILENAME)

    # optionally clear out competitor containers at the end of the run
    # One one hand, it may be useful to leave them in to be able to poke at logs. On the other
    # hand, then they need to be removed manually by the user, and that can get tedious
    if args["clean_competitor_containers"]:
        # remove bot containers

        # todo: wait for up to X seconds for competitor containers to shut down before calling this
        cmd = ["lxc", "rm",] + comp_container_names
        run_subproc_and_print_output(cmd)


if __name__ == "__main__":
    main()
