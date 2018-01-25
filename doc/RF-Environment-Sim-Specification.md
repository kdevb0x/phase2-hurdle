![SC2 Banner](resources/SC2_Banner.png)
https://spectrumcollaborationchallenge.com

# RF Environment Simulator
The RF Environment Simulator is used to allow competitor radios to communicate amongst themselves and interact with Bot radios over a simulated RF channel. The simulator is implemented in [GNU Radio](https://www.gnuradio.org/) and incorporates an [out-of-tree module](https://wiki.gnuradio.org/index.php/OutOfTreeModules) named gr-envsim.

The details below will assist you in successfully integrating your design with the RF Environment Simulator. The expectation is that competitors will use GNU Radio based designs to complete the Phase 2 Hurdle. Competitors not intending to use GNU Radio in their solutions are strongly encouraged to at mimumum use GNU Radio for the portion of their design that interfaces with the RF Environment Simulator. This SC2 provided [out-of-tree module](../gr-envsim/) provides custom GNU Radio blocks to help. A debug mode is available to help visualize what transmissions appear in the RF Environment. See the documentation for this debug mode [here](Envsim-Debug-Mode.md)

## Environment Simulator Features
The RF Environment Simulator has two primary design goals:
1. Simulate a real time streaming device permitting bursty transmissions
2. Simulate a USRP interface to reduce the development effort required to integrate existing radio designs


### Real Time Streaming
To achieve the the first goal, the RF Environment Simulator uses an **envsim_source** block to accept
timestamped packets from clients and zero fill any gaps in time. This allows clients to transmit continuously or in a bursty manner and ensures that time progresses in a realistic manner. Packets that
show up late will be dropped.

Samples from multiple clients will be combined in a flowgraph that imparts channel noise and can apply
impairments such as transmit power limitations, local oscillator offsets, and timing errors.

### USRP Interface
The RF Environment Simulator achieves the second goal through duplicating the interfaces provided by
blocks in GNU Radio's [gr-uhd](https://gnuradio.org/doc/doxygen/page_uhd.html) module. The most important
blocks to pay attention to are the [gr::uhd::usrp_source](https://gnuradio.org/doc/doxygen/classgr_1_1uhd_1_1usrp__source.html) and [gr::uhd::usrp_sink](https://gnuradio.org/doc/doxygen/classgr_1_1uhd_1_1usrp__sink.html) blocks. Both are derived from [gr::uhd::usrp_block](https://gnuradio.org/doc/doxygen/classgr_1_1uhd_1_1usrp__block.html).

The RF Environment Simulator mirrors the interfaces provided by these blocks using:
* [envsim::env_source.h](../gr-envsim/include/envsim/env_source.h): Receives samples from the environment simulator and makes them available to the flowgraph
* [envsim::env_sink.h](../gr-envsim/include/envsim/env_sink.h): Accepts samples from the rest of the flowgraph and sends them to the environment simulator
* [envsim::env_block.h](../gr-envsim/include/envsim/env_block.h): Incorporates functions common to the source and sink blocks
* [envsim::socket_meta_pdu.h](../gr-envsim/include/envsim/socket_meta_pdu.h): Handles arbitrary PDU messages from a flowgraph, serializes them to character strings, and sends out a UDP socket. Also handles incoming network packets, deserializes them back into PDU messages, and provides them to the flowgraph.

### envsim::env_block.h Reference
All functions in the [gr::uhd::usrp_block](https://gnuradio.org/doc/doxygen/classgr_1_1uhd_1_1usrp__block.html) are declared in the envsim::env_block.h. Any functions not called out below as **Functions with No Effect** or **Implemented Functions** are **unimplemented** and will raise a runtime exception if used.

#### Functions with No Effect
* get_mboard_sensor_names
* set_time_now
* set_subdev_spec
* set_samp_rate
* set_center_freq
* set_gain
* set_antenna

#### Implemented Functions

##### `public uhd::time_spec_t ` `get_time_now` `(size_t mboard)`

Get the current time registers.

##### Parameters
* `mboard` the motherboard index 0 to M-1

##### Returns
the current usrp time


### envsim::env_sink.h Reference
The envsim::env_sink block inherits from [envsim::env_block.h](../gr-envsim/include/envsim/env_block.h) and is intended to emulate the [gr::uhd::usrp_sink](https://gnuradio.org/doc/doxygen/classgr_1_1uhd_1_1usrp__sink.html) block. It accepts streaming complex samples, bundles them into timestamped messages, and passes them out to a [envsim::socket_meta_pdu.h](../gr-envsim/include/envsim/socket_meta_pdu.h) block.

This block consumes stream tags similarly to the [gr::uhd::usrp_sink](https://gnuradio.org/doc/doxygen/classgr_1_1uhd_1_1usrp__sink.html) block to enable bursty transmissions. More detail on this can be found [here](Timed-Transmissions-with-Stream-Tags.md). Other topics to research include GNU Radio Stream Tags [here](https://wiki.gnuradio.org/index.php/Guided_Tutorial_Programming_Topics#5.2_Stream_Tags) and [here](https://gnuradio.org/doc/doxygen/page_stream_tags.html) as well as the **TX Stream tagging** section [here](https://gnuradio.org/doc/doxygen/classgr_1_1uhd_1_1usrp__sink.html)

This block will use either the "tx_sob"/"tx_eob" tag pairs approach or the "tagged_stream" approach. Leave the "tx_pkt_len_name" parameter in the env_sink constructor blank to use "tx_sob"/"tx_eob" tag pairs.


### envsim::env_source.h Reference
The envsim::env_source block inherits from [envsim::env_block.h](../gr-envsim/include/envsim/env_block.h) and is intended to emulate the [gr::uhd::usrp_source](https://gnuradio.org/doc/doxygen/classgr_1_1uhd_1_1usrp__source.html) block. It accepts messages from a [envsim::socket_meta_pdu.h](../gr-envsim/include/envsim/socket_meta_pdu.h) block and outputs them as blocks of complex baseband samples.



