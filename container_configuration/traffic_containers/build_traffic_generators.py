#!/usr/bin/env python3
import pylxd
import subprocess
import sys
import os
# making a traffic generator for each node of the bot and each node of the competior network
NUM_TRAFFIC_GENS = 6

MGEN_BIN_PATH = "/root/MGEN/mgen"

MGEN_DEST_PATH = "/usr/local/bin/mgen"
MGEN_SERVICE_FILE = "mgen.service"
MGEN_SERVICE_PATH ="/lib/systemd/system/"

DEV_IP_BASE = 101
DEV_NETMASK = "255.255.255.0"
DEV_CONFIG_DEST_PATH = "/etc/network/interfaces.d/tr0.cfg"

TGEN_NW_INTERFACES_FILE = "tgen_network_interfaces"
TGEN_NW_INTERFACES_DEST_PATH = "/etc/network/interfaces"

def write_inet_device_config_dict(name, address, parent):
    '''
    Write out a device config dict in the format expected by pylxd
    '''

    dev_cfg = {
        name:{
            "ipv4.address": address,
            "name": name,
            "nictype": "bridged",
            "parent": parent,
            "type": "nic"
        }
    }
    return dev_cfg

def write_inet_device_config_file(file_name, dev_name, address, netmask, gateway):
    '''
    Write out a device config file expected in /etc/network/interfaces.d
    '''
    with open(file_name, "w") as f:
        print("auto {}".format(dev_name), file=f)
        print("iface {} inet static".format(dev_name), file=f)
        print("    address {}".format(address), file=f)
        print("    netmask {}".format(netmask), file=f)
        print("",file=f)
        print("# set up static traffic route", file=f)
        print("up route add -net 192.168.0.0/16 gw {} dev {}".format(gateway, dev_name), file=f)

    return



def main():



    # working with 6 traffic generator containers
    tgen_container_names = ["tgen{}".format(i) for i in range(1,NUM_TRAFFIC_GENS+1)]

    lxd_client = pylxd.Client()

    my_containers = lxd_client.containers.all()

    my_container_names = [c.name for c in my_containers]

    name_conflict_found = False
    for name in my_container_names:
        if name in tgen_container_names:
            print("Name conflict found in list of containers, please remove container {}".format(name))
            name_conflict_found = True

    if name_conflict_found:
        print("At least one container name conflict found, please clear out container list and retry")
        sys.exit(1)
    else:
        print("No name conflicts found, generating container list: {}".format(tgen_container_names))


    for i, cont_name in enumerate(tgen_container_names):

        print("Creating {}".format(cont_name))
        config = {"name":cont_name,
                "source":{"type":"image", "alias":"ubuntu/xenial"}}

        container = lxd_client.containers.create(config, wait=True)
        container.config["security.nesting"] = "true"


        # Setting up networking for tr0 interface
        dev_name = "tr0"
        dev_ip = "192.168.{}.2".format(DEV_IP_BASE+i)
        dev_gw = "192.168.{}.1".format(DEV_IP_BASE+i)

        dev_config = write_inet_device_config_dict(name=dev_name,
                                                   address=dev_ip,
                                                   parent="trbr{}".format(i+1))

        print("adding device:{}".format(dev_config))
        container.devices=dev_config

        container.save()

        # writing network interface temporary config files
        file_name = "{}_{}.cfg".format(cont_name, dev_name)
        write_inet_device_config_file(file_name=file_name,
                                      dev_name=dev_name,
                                      address=dev_ip,
                                      netmask=DEV_NETMASK,
                                      gateway=dev_gw)

        # save temp config files to containers
        push_cmd = ["lxc", "file", "push", file_name, cont_name+DEV_CONFIG_DEST_PATH]
        print("installing {} interface config file".format(dev_name))
        print("running {}".format(" ".join(push_cmd)))
        subprocess.run(push_cmd)

        # have /etc/network/interfaces source /etc/network/interfaces.d/*
        push_cmd = ["lxc", "file", "push", TGEN_NW_INTERFACES_FILE, cont_name+TGEN_NW_INTERFACES_DEST_PATH]
        print("installing interface config file")
        print("running {}".format(" ".join(push_cmd)))
        subprocess.run(push_cmd)

        # install MGEN binary
        push_cmd = ["lxc", "file", "push", MGEN_BIN_PATH, cont_name+MGEN_DEST_PATH]
        print("installing MGEN binary")
        print("running {}".format(" ".join(push_cmd)))
        subprocess.run(push_cmd)

        # Install MGEN service file
        push_cmd = ["lxc", "file", "push", MGEN_SERVICE_FILE, cont_name+MGEN_SERVICE_PATH]
        print("Configuring MGEN service")
        print("running {}".format(" ".join(push_cmd)))
        subprocess.run(push_cmd)

        # add mgen user
        print("adding MGEN user")
        container.start(wait=True)
        container.execute(["adduser", "mgen", "--shell=/bin/false"])
        container.stop(wait=True)

        # switching to starting MGEN service manually instead of at boot
        # # enable mgen service
        # print("Enabling MGEN service")
        # container.start(wait=True)
        # container.execute(["systemctl", "enable", "mgen"])
        # container.stop(wait=True)


if __name__ == "__main__":
    main()
