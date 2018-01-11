#!/usr/bin/env python3

import argparse

import pylxd


def control_container(client, cont_name, action):
    '''
    given an instance of the lxd client and the container name, perform the specified action
    (start or stop)
    '''
    try:
        container = client.containers.get(cont_name)
        print("{}ing container {}".format(action, cont_name))
        if action == "start":
            container.start(wait=True)
        elif action == "stop":
            container.stop(wait=True)
        else:
            raise NameError("Uknown action specified: {}".format(action))

    except pylxd.exceptions.LXDAPIException as err:
        print("error when trying to {} container {}".format(action, cont_name))
        raise(err)


def main():

    # set up command line args
    parser = argparse.ArgumentParser(prog="container_control",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--competitor-container-name-base', default="competitor-hurdle-srn", dest="comp_base",
                        help="Competitor container name prefix, no container number")
    parser.add_argument('--bot-container-name-base', default="darpa-practice-srn", dest="bot_base",
                        help="Bot container name prefix, no container number")
    parser.add_argument('--tgen-container-name-base', default="tgen", dest="tgen_base",
                        help="Traffic generator container name prefix, no container number")

    parser.add_argument('action', choices=["start", "stop"],
                        help="start or stop the containers")

    # parse args and store to dictionary
    args = vars(parser.parse_args())


    # get list of all known container names
    lxd_client = pylxd.Client()

    # get list of current container names to chec for conflicts
    my_containers = lxd_client.containers.all()
    my_container_names = [c.name for c in my_containers]

    # find traffic container names
    tgen_container_names = [name for name in my_container_names if name.startswith(args["tgen_base"])]

    # find bot container names
    bot_container_names = [name for name in my_container_names if name.startswith(args["bot_base"])]

    # find competitor container names
    comp_container_names = [name for name in my_container_names if name.startswith(args["comp_base"])]

    # TODO: Throw warnings or errors if expected numbers of containers aren't found

    # combine container names into single list for simple iteration
    container_names = tgen_container_names + bot_container_names + comp_container_names

    for cont_name in container_names:
        control_container(lxd_client, cont_name, args["action"])


if __name__ == "__main__":
    main()
