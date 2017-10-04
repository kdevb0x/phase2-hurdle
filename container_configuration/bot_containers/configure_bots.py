#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

import pylxd

# TODO: pull these from common config file for sanity's sake
MGEN_DEST_PATH = "/usr/local/bin/mgen"
TR0_IP_BASE = 101
CAN0_IP_BASE = 101
CAN0_MTU = 32768
COL0_IP_BASE = 101
USRP0_IP_BASE = 101

NW_INTERFACE_CONFIG_DEST_PATH = "/etc/network/interfaces.d"

PRACTICE_BOT_NAME_PATTERN = "darpa-practice-srn"
HURDLE_BOT_NAME_PATTERN = "darpa-hurdle-srn"

IMAGE_PATH = "/share/nas/competitor/images/"

def update_inet_device_config_dict(dev_config_dict, name, address, parent, **kwargs):
    '''
    Write out a device config dict in the format expected by pylxd
    '''

    dev_config_dict[name] = {
        "ipv4.address": address,
        "name": name,
        "nictype": "bridged",
        "parent": parent,
        "type": "nic"
    }

    # add any extra specified keyword args
    for key, val in kwargs.items():
        dev_config_dict[name][key] = val

    return dev_config_dict

def write_inet_device_config_file(file_name, dev_name, address, netmask):
    '''
    Write out a device config file expected in /etc/network/interfaces.d
    '''
    with open(file_name, "w") as f:
        print("auto {}".format(dev_name), file=f)
        print("iface {} inet static".format(dev_name), file=f)
        print("    address {}".format(address), file=f)
        print("    netmask {}".format(netmask), file=f)

    return

def configure_container_inet_device(client, cont_name, dev_name, address, parent, netmask, **kwargs):
    '''
    Update the container device dictionary with a new ethernet device, save the new configuration
    to the container, create a temporary network interface file, and store that file in the
    container in /etc/network/interfaces.d/
    '''

    # get current device config
    container = client.containers.get(cont_name)
    dev_config_dict = container.devices

    # add device to devices dict
    print("adding device {} to container {}".format(dev_name, cont_name))
    dev_config_dict = update_inet_device_config_dict(dev_config_dict=dev_config_dict,
                                                     name=dev_name,
                                                     address=address,
                                                     parent=parent)
    # update container
    container.devices=dev_config_dict
    container.save()

    # write network interface temporary config file
    file_name = "{}_{}.cfg".format(cont_name, dev_name)
    write_inet_device_config_file(file_name=file_name,
                                    dev_name=dev_name,
                                    address=address,
                                    netmask=netmask,
                                    )

    # save temp config files to containers
    dest_file_name = "{}.cfg".format(dev_name)

    # push temporary file into container
    push_cmd = ["lxc", "file", "push", file_name, cont_name+os.path.join(NW_INTERFACE_CONFIG_DEST_PATH, dest_file_name)]
    print("installing {} interface config file".format(dev_name))
    print("running {}".format(" ".join(push_cmd)))
    subprocess.run(push_cmd)

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

def main():

    # set up command line args
    parser = argparse.ArgumentParser(prog="configure_bots",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--image-name', default="darpa-practice-srn-base-v1-0-0.tar.gz",
                        help="The lxc image name we'll generate containers from, assumed to be in /share/nas/competitor/images/")
    parser.add_argument('--bot-type', choices=["practice", "hurdle"],
                        default="practice", help="What type of bot is this?")
    parser.add_argument('--num-containers', default=3, type=int,
                        help="How many containers we are standing up")

    # parse args and store to dictionary
    args = vars(parser.parse_args())

    if args["bot_type"] == "practice":
        container_name_pattern = PRACTICE_BOT_NAME_PATTERN
    else:
        container_name_pattern = HURDLE_BOT_NAME_PATTERN

    # working with N bot containers. Build up list of container names
    bot_container_names = [container_name_pattern+"{}".format(i) for i in range(1,args["num_containers"]+1)]

    lxd_client = pylxd.Client()

    # get list of current container names to check for conflicts
    my_containers = lxd_client.containers.all()
    my_container_names = [c.name for c in my_containers]


    # remove any existing bot containers of the same type
    for name in my_container_names:
        if name in bot_container_names:
            print("Existing bot container found, removing container {}".format(name))

            cmd = ["lxc", "rm", name]
            run_subproc_and_print_output(cmd)




    # Import image
    full_image_path = os.path.join(IMAGE_PATH, args["image_name"])

    # strip off the .gz on the end of the image name
    image_alias = os.path.splitext(args["image_name"])[0]

    # strip off the remaining .tar on the end of the image name
    image_alias = os.path.splitext(image_alias)[0]

    print("Importing image alias {} from {}".format(image_alias, full_image_path))

    cmd = ["lxc", "image", "import", full_image_path, "--alias", image_alias]
    run_subproc_and_print_output(cmd)

    # check if the image import was successful
    my_images = lxd_client.images.all()
    my_image_names = [alias["name"] for image in my_images for alias in image.aliases ]

    # if image name not found, list the images we know about and exit
    if image_alias not in my_image_names:
        print("Image alias: {} not found. Check for typos.".format(image_alias))
        print("Here is the current list of known image aliases:")
        print(my_image_names)
        sys.exit(1)

    print("generating container list: {}".format(bot_container_names))

    # stand up bots
    for i, cont_name in enumerate(bot_container_names):

        print("Creating {}".format(cont_name))
        config = {"name":cont_name,
                "source":{"type":"image", "alias":image_alias}}

        container = lxd_client.containers.create(config, wait=True)
        container.config["security.nesting"] = "true"

        # clear out existing devices and save
        dev_config_dict = {}
        container.devices = dev_config_dict
        container.save()

        # Setting up networking for bots
        # tr0 interfaces first

        tr0_name = "tr0"
        tr0_ip = "192.168.{}.1".format(TR0_IP_BASE+i)
        tr0_netmask = "255.255.255.0"
        tr0_parent = "trbr{}".format(i+1)

        # set up the tr0 interface for the current container
        configure_container_inet_device(client=lxd_client,
                                        cont_name=cont_name,
                                        dev_name=tr0_name,
                                        address=tr0_ip,
                                        parent=tr0_parent,
                                        netmask=tr0_netmask)

        # Next CAN interface. Note, only accessible to bots.
        can0_name = "can0"
        can0_ip = "172.16.{}.2".format(CAN0_IP_BASE+i)
        can0_netmask = "255.255.0.0"
        can0_parent = "canbr0"

        # set up the can0 interface for the current container
        configure_container_inet_device(client=lxd_client,
                                        cont_name=cont_name,
                                        dev_name=can0_name,
                                        address=can0_ip,
                                        parent=can0_parent,
                                        netmask=can0_netmask,
                                        mtu=CAN0_MTU)


        # Next COL interface. Note that this schema expects that the collaboration server will be
        # listening on subnet 172.30.COL0_IP_BASE.0
        col0_name = "col0"
        col0_ip = "172.30.{}.{}".format(COL0_IP_BASE, COL0_IP_BASE+i)
        col0_netmask = "255.255.255.0"
        col0_parent = "colbr0"

        # set up the col0 interface for the current container
        configure_container_inet_device(client=lxd_client,
                                        cont_name=cont_name,
                                        dev_name=col0_name,
                                        address=col0_ip,
                                        parent=col0_parent,
                                        netmask=col0_netmask)


        # Next USRP interface.
        usrp0_name = "usrp0"
        usrp0_ip = "192.168.40.{}".format(USRP0_IP_BASE+i)
        usrp0_netmask = "255.255.255.0"
        usrp0_parent = "usrpbr0"


        # set up the usrp0 interface for the current container
        configure_container_inet_device(client=lxd_client,
                                        cont_name=cont_name,
                                        dev_name=usrp0_name,
                                        address=usrp0_ip,
                                        parent=usrp0_parent,
                                        netmask=usrp0_netmask)


if __name__ == "__main__":
    main()
