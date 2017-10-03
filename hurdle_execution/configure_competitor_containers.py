#!/usr/bin/env python3

import argparse
import hashlib
import os
import subprocess
import sys

import pylxd

NUM_BOT_CONTAINERS = 3
NUM_COMPETITOR_CONTAINERS = 3
CONTAINER_NAME_PATTERN="competitor-hurdle-srn"
IMAGE_PATH = "/share/nas/competitor/images/"
IMAGE_ALIAS = "competitor-image"
BUF_SIZE=65536*16

TR0_IP_BASE = 101
COL0_IP_BASE = 101
USRP0_IP_BASE = 101

NW_INTERFACE_CONFIG_DEST_PATH = "/etc/network/interfaces.d"

def get_image_export_fingerprint(image_file):
    '''
    Get the fingerprint of our image export
    '''
    sha256 = hashlib.sha256()
    with open(os.path.join(IMAGE_PATH, image_file), 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break

            sha256.update(data)

    return sha256.hexdigest()


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


def main():

    # set up command line args
    parser = argparse.ArgumentParser(prog="configure_competitor_containers",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--image-file', default="competitor-image.tar.gz",
                        help="The lxc image file in /share/nas/competitor/images/ we'll generate containers from")

    # parse args and store to dictionary
    args = vars(parser.parse_args())


    # set up range of SRN numbers to work with
    start_srn_num = NUM_BOT_CONTAINERS+1
    end_srn_num = NUM_BOT_CONTAINERS+NUM_COMPETITOR_CONTAINERS+1

    # working with 3 competitor containers. Build up list of container names
    comp_container_names = [CONTAINER_NAME_PATTERN+"{}".format(i) for i in range(start_srn_num, end_srn_num)]

    lxd_client = pylxd.Client()

    # get list of current container names to chec for conflicts
    my_containers = lxd_client.containers.all()
    my_container_names = [c.name for c in my_containers]

    name_conflict_found = False
    for name in my_container_names:
        if name in comp_container_names:
            print("Name conflict found in list of containers, please remove container {}".format(name))
            name_conflict_found = True

    if name_conflict_found:
        print("At least one container name conflict found, please clear out container list and retry")
        sys.exit(1)
    else:
        print("No name conflicts found, generating container list: {}".format(comp_container_names))

    # just in case there's a weird conflict later, use a temp variable for the image alias name
    current_image_alias = IMAGE_ALIAS

    # check if the image file we specified exists
    try:

        image_filepath = os.path.join(IMAGE_PATH, args["image_file"])
        print("attempting to load image from {}".format(image_filepath))
        with open(image_filepath, 'rb') as f:
            image = lxd_client.images.create(f, wait=True)
            image.add_alias(current_image_alias, description="potential competitor hurdle solution")
    except FileNotFoundError as err:
        print("File: {} not found in {}, exiting".format(args["image_file"],IMAGE_PATH))
        sys.exit(1)
    except pylxd.exceptions.LXDAPIException as err:

        # warn if this fingerprint exists, but continue anyhow
        if str(err) == "Image with same fingerprint already exists":
            print("warning, image with same fingerprint has been loaded previously. Make sure this is the image you intended")

            # get an alias that works so we can go forward
            # first get our fingerprint
            fingerprint = get_image_export_fingerprint(args["image_file"])


            # now get image associated with that fingerprint
            loaded_image = lxd_client.images.get(fingerprint)

            # if there's an alias defined, load the first one into current_image_alias.
            if len(loaded_image.aliases) > 0:
                current_image_alias = loaded_image.aliases[0]["name"]
                print("now using alias {}".format(current_image_alias))
            else:
                print("existing image has no alias. Can't recover")
                print("Please ensure the image you specified is not required for the hurdle")
                print("if it is not required internally by this hurdle, remove the image with fingerprint {}".format(fingerprint))
                sys.exit(1)


        else:
            print("Error loading image: Check if it has already been loaded by running 'lxc image list'")
            print("Error was: {}".format(err))
            sys.exit(1)

    my_images = lxd_client.images.all()
    my_image_names = [alias["name"] for image in my_images for alias in image.aliases ]

    print("image load was successful. Current image list now {}".format(my_image_names))


    # stand up competitor containers
    for i, cont_name in enumerate(comp_container_names):

        config = {"name":cont_name,
                  "source":{"type":"image", "alias":current_image_alias}}

        print("Creating {} with config {}".format(cont_name, config))

        container = lxd_client.containers.create(config, wait=True)
        container.config["security.nesting"] = "true"

        # clear out existing devices and save
        dev_config_dict = {}
        container.devices = dev_config_dict
        container.save()

        # Setting up networking for bots
        # tr0 interfaces first

        tr0_name = "tr0"
        tr0_ip = "192.168.{}.1".format(TR0_IP_BASE+NUM_BOT_CONTAINERS+i)
        tr0_netmask = "255.255.255.0"
        tr0_parent = "trbr{}".format(NUM_BOT_CONTAINERS+i+1)

        # set up the tr0 interface for the current container
        configure_container_inet_device(client=lxd_client,
                                        cont_name=cont_name,
                                        dev_name=tr0_name,
                                        address=tr0_ip,
                                        parent=tr0_parent,
                                        netmask=tr0_netmask)


        # Next COL interface. Note that this schema expects that the collaboration server will be
        # listening on subnet 172.30.COL0_IP_BASE.0
        col0_name = "col0"
        col0_ip = "172.30.{}.{}".format(COL0_IP_BASE, NUM_BOT_CONTAINERS+COL0_IP_BASE+i)
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
        usrp0_ip = "192.168.40.{}".format(NUM_BOT_CONTAINERS+USRP0_IP_BASE+i)
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
