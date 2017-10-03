![SC2 Banner](resources/SC2_Banner.png)
https://spectrumcollaborationchallenge.com

# Practice Bot Specification
## Overview of the Bots
### Bot Multi-Frequency TDMA (MF-TDMA) Scheme

In the “Increment 1” version, Bots communicate using QPSK at the physical layer, and Multi-Frequency TDMA (MF-TDMA) at the MAC layer.  In the MF-TDMA scheme, Bots organize their transmissions across multiple time and frequency slots. 

The MF-TDMA time slots are organized into (repeating) epochs, whose duration is currently 400 msec.  This epoch duration is divided equally among the specified number of time slots.  Bots currently communicate with a MF-TDMA pattern spanning the entire bandwidth of the hurdle, divided equally among the specified number of frequency slots. 

### STATIC and REACTIVE modes

There are two modes for the MF-TDMA MAC scheme.  In the STATIC mode, the time-frequency slot allocations are specified statically, via a JSON-based configuration file.  In the REACTIVE mode, these slot allocations are updated dynamically by a separate "Remapper" process that runs on the Master Bot, according to observed network performance. The Practice Bots use REACTIVE mode.

Note: The Practice Bots only adapt to their own interference. They don't attempt to mitigate interference to other networks in the scenario.

### Bot Collaboration Channel Support

If a Competitor CIRN sends out an InformationalDeclaration message on the SC2 Collaboration Channel, this message is received by the REACTIVE Bot Collaboration Client (collab client) running on the Master Bot (which is always the Collaboration Gateway).  The Master Bot will interpret the scalar_performance_metric S field of this message as a measure of the normalized goodput currently achieved by that CIRN, e.g.

* S = 0 is interpreted to mean that the CIRN is not able to service any of its offered traffic load
* S = 1 is interpreted to mean that the CIRN is able to service its entire traffic load (all ingress packets are successfully received at their respective destinations)

The Master Bot will periodically update its time-frequency slot assignments to optimize the sum of its own normalized goodput with that reported by the other CIRNs in the scenario.  Conversely, each Master Bot will send its own achieved normalized goodput to all of its Collaboration Channel peers, using the same Collaboration Protocol message. The network_id field within the InformationalDeclaration message will be used to distinguish among the CIRNs in a scenario. 


For the current release, the Bots will ignore all fields other than the scalar_performance_metric and network_id field.
 
## Bot Description
### Bot Initialization

The Bots go through several steps when starting. These steps can vary depending on the particular bot.  The Master Bot will also start the remapper and collab client.  Other than the Master Bot, all the Bots follow the same start up process. Their start up steps are:

1. Start the Bot Discovery Agent
2. Start the Remapper (for the Master Bot)
3. Start the Collab Client (for Master Bot)
4. Setup IP routing
5. Start the GNU Radio Flowgraph

In the current version of the Practice Bots this entire startup process has been automated with an Ubuntu Upstart script.  Upstart is an init system similar to SystemD.

Here are some details about each step.

#### Step 1: Bot Discovery

The first step performed by the Bots is to initiate a rendezvous of the Bot containers in the network. Once the Bot Discovery Agent has been started the Bots will share their network information with each other. This will allow them to properly route IP packets from the Hurdle Traffic Generator according to the MF-TDMA mapping specified in the Bot config file. Note, the interface used by the Bot Discovery Agent is only available to Practice and Hurdle Bots. Competitor solutions must perform an over the air rendezvous.

The information the Bots share is only the Standard Radio Node (SRN) ID and the IP Address, for example:

* SRN ID = 1, IP Address 172.16.101.2
* SRN ID = 2, IP Address 172.16.102.2
* SRN ID = 3, IP Address 172.16.103.2

Note that these three Bots make up one "Bot Network" and they all share the same Network ID.


#### Step 2: Start Remapper

The Practice Bots start a separate process known as the "Remapper" on the SRN designated to be the Master Bot node (the Master Bot).  This process dynamically assigns Bot links to MF-TDMA slots based on observed interference.


#### Step 3: Start Collaboration Client

Next, the Practice Bots initiate the Collaboration Client (collab client). The collab client the Bots use is a modified version of the collab client that can be found in [collab_protocol/python/collab_client.py](../collab_protocol/python/collab_client.py). The modifications allow for daemonizing the collab client and for communication with the remapper. The only way to collaborate with the Bots is the Collaboration Channel.


#### Step 4: Setup Packet Routes

Next, the Bots setup routing between the MGEN traffic (coming from the tr0 interface) and the GNU Radio flowgraph (which consumes packets from the tun0 interface).


#### Step 5: Start Bot Transceiver Flowgraph

Finally, the Bot flowgraph will be started on each Bot container independently.  The flowgraph requires two critical arguments: the Bot ID to assign to the Bot, which is used to assign time and frequency channels and the path to the Bot configuration file.

## Description of the Bot Configuration File
 
The Bots require a config file named radio.conf in /root/radio_api/. The Bot config file parameters are described below.  Most of the items in the config file can be left to the default options in the Example below; however there are a few items that you may want to change and there are a few items that are dependent on each other.  Here is a description of each field in the config file:
 
* **BOT_MODE** Can be either "STATIC" or "REACTIVE" (NOTE: "REACTIVE" is required for the Bots to be Collaborative.)
* **MODE_OPTIONS** These are the options for the given mode.  There are two sets of options to configure depending on the traffic generator.
    * **GENERATOR** Must be "NETWORK" (Note: "PACKET_SOURCE" is no longer supported.)
        * **NETWORK** Configure the Bot network to accept packets via a given network device
            * **DEVICE** The network device to use, usually "tun0"
            * **MTU** The maximum transmission unit (MTU) to use.  Packets with size greater than the MTU will be dropped.  At this time only setting the MTU to 1000 has been tested.
            * **CONFIG_PORT** (Not currently used)
* **INIT_ASSIGN**: This input is a matrix specifying the mapping of links to time and frequency slots.  The rows of the matrix represent frequency slots, and the columns represent time slots.  The ij-th entry of the table is the Link ID assigned to the i-th frequency slot and j-th time slot.  The default input is:
```text
"INIT_ASSIGN": [[ 0,  1,  2],
                  [ 3,  4,  5]],
```
In this example, Link ID 5 is assigned to Frequency Slot 2 and Time Slot 3.
It is possible to assign a Link ID to multiple slots, or not assign it to any slots.  Link IDs are enumerated in ascending order of the transmitting Bot ID in the link, first, and receiver Bot ID, second.  The Link ID assignments for a 5-Node Bot network are given in Table A.1 in the Appendix.
Frequency slots are enumerated from lowest to highest frequency slot.
 
* **NUM_NODES** The number of Bot nodes in the network.  This must be an integer between 2 and 5.  (NOTE: The number of elements in INIT_ASSIGN must equal (NUM_NODES) * (NUM_NODES - 1).  So in the default case of NUM_NODES = 5, the INIT_ASSIGN table will have 5x4 = 20 elements.)
* **USE_BOT_DISCOVERY** Turns on bot discovery, an out of band agent that each bot uses to find the other Bots in it the bot network. (Default = true) 
* **USE_COLOSSEUM_INI** Instructs the bot use use the Colosseum INI file, if false the bot will use default options. (Default = true) 
* **BOT_DISCOVERY_NETWORK_ID** Set to any positive integer which is distinct for each Bot network running in the Batch job. 
* **FC_OFFSET** The offset, in Hz, from the given center frequency. (Default = 5e6) (Not used in the Hurdle)
* **TX_GAIN** The transmit gain, in dB, as set on the USRP (Not used in the Hurdle)
* **RX_GAIN**  The receive gain, in dB, as set on the USRP (Not used in the Hurdle)
 
## Example Bot Radio.conf File
Below is an example bot config file, it is also the recommended configuration. Note that parameters such as FC_OFFSET, TX_GAIN, and RX_GAIN are not used by the Hurdle framework, only by the actual Colosseum. 

```python
{
    "BOT_MODE": "REACTIVE",
    "MODE_OPTIONS": {"GENERATOR": "NETWORK", "DEVICE": "tun0", "MTU": 1000, "CONFIG_PORT": 34000},
    "INIT_ASSIGN": [[ 0,  1,  2],
                    [ 3,  4,  5]],
    "NUM_NODES" : 3,
    "USE_BOT_DISCOVERY": true,
    "USE_COLOSSEUM_INI": true,
    "BOT_DISCOVERY_NETWORK_ID": 1,
    "FC_OFFSET": 5e6,
    "TX_GAIN": 20,
    "RX_GAIN": 20
}
```

## A. Appendix

### A.1. Link ID Assignments

| Link ID | Transmitting Bot ID | Receiving Bot ID |
|---------|---------------------|------------------|
|0        | 0                   | 1 |
|1        | 0                   | 2 |
|2        | 0                   | 3 |
|3        | 0                   | 4 |
|4        | 1                   | 0 |
|5        | 1                   | 2 |
|6        | 1                   | 3 |
|7        | 1                   | 4 |
|8        | 2                   | 0 |
|9        | 2                   | 1 |
|10       | 2                   | 3 |
|11       | 2                   | 4 |
|12       | 3                   | 0 |
|13       | 3                   | 1 |
|14       | 3                   | 2 |
|15       | 3                   | 4 |
|16       | 4                   | 0 |
|17       | 4                   | 1 |
|18       | 4                   | 2 |
|19       | 4                   | 3 |

