![SC2 Banner](resources/SC2_Banner.png)
https://spectrumcollaborationchallenge.com

# Introduction
This document is intended to provide an introduction into how a type of metadata called "stream tags" in GNU Radio can be used to enable timed transmissions of bursty data. This technique can be very useful when attempting to develop a radio for use in the Phase 2 Hurdles.

## Stream Tags
Stream tags are metadata objects that can be associated with a particular sample in a GNU Radio flowgraph. A stream tag consists of the following fields: **offset**, **key**, **value**, and an optional **srcid**. Fields other than the **offset** field are encoded as Polymorphic data types, or PMTs. At a high level, PMTs serve as containers for many data types, which allows the **value** field to include strings, integers, floats, or even Python-like dictionaries. See [here](https://gnuradio.org/doc/doxygen/page_pmt.html) for the official GNU Radio documentation on polymorphic types. See below for a summary of each field used in a Stream Tag:

* **offset**: The unsigned 64 bit integer containing the absolute sample count that the tag is associated with. The sample count starts at zero, beginning at the time the GNU Radio application starts.

* **key**: The PMT encoded string serving as the field identifier. This is what allows an application to filter on only the stream tags it needs and anticipate the data type of the associated **value** field. Example strings for the key field would be "tx_sob", "tx_eob", "tx_time", "tx_packet_len".

* **value**: This is the data payload for the stream  tag. Tags such as tx_packet_len will include a PMT encoded double for the value. Other stream tags don't actually require a value, and will use either a PMT_NIL (ie a null) or PMT encoded booleans for the value field.

* **srcid**: This optional field is used to note which GNU Radio block generated a specific tag. This can be useful when debugging complex flowgraphs, or a graph where multiple blocks are capable of generating the same type of stream tag. The **srcid** field is a PMT encoded string.

For more information on Stream Tags, see the official GNU Radio Stream Tag documentation [here](https://gnuradio.org/doc/doxygen/page_stream_tags.html)

## Stream Tags Used by the Environment Simulator
The environment simulator uses two different groups of stream tags to control when a given block of samples will be transmitted into the environment. This reflects the two different ways the gr-uhd USRP Sink block uses stream tags. The environment simulator is intended to emulate the behavior of the usrp_sink block in GNU Radio. See the TX Stream Tagging section [here](https://gnuradio.org/doc/doxygen-3.7/classgr_1_1usrp__sink.html) for the official GNU Radio documentation on how the usrp_sink block handles bursty transmissions using stream tags.

### Original Timed Burst Approach
In the first and oldest style of usage, the "tx_sob", "tx_time", and "tx_eob" stream tags are used to control burst timing. "tx_sob" refers to Transmit, Start of Burst. The "tx_time" tag includes the time at which this burst is supposed to begin. Both of these tags must be associated with the first sample of the transmit burst. The "tx_eob" tag refers to Transmit, End of Burst. This tag must be associated with the last sample of a burst.

To use this style of transmit time tagging with the environment simulator, leave the "tx_pkt_len_name" parameter in the env_sink constructor blank in your radio application.

See below for a detailed description of the expected tag contents for each type of tag used in this style of timed burst.

#### tx_sob

* **offset**: sample number associated with the start of a burst. The offset for a tx_sob tag, in general, should be exactly one sample after the preceding tx_eob tag.

* **key**: PMT encoded string "tx_sob"

* **value**: PMT data type. This is not used by downstream blocks. Generally a PMT encoded boolean True value.

#### tx_time

* **offset**: sample number associated with the start of a burst. tx_time tags must occur on the same sample number as a tx_sob tag.

* **key**: PMT encoded string "tx_time"

* **value**: PMT encoded tuple of values. The first item in the pair is the PMT encoded uint64 epoch time (wall time). The second item in the pair is the PMT encoded double fractional epoch time. An epoch timestamp of 1416299676.3453495 would appear as (1416299676, 0.3453495).

#### tx_eob

* **offset**: sample number associated with the end of a burst

* **key**: PMT encoded string "tx_eob"

* **value**: PMT data type. This is not used by downstream blocks. Generally a PMT encoded boolean True value.


### Tagged Stream Timed Burst Approach
In GNU Radio, a tagged stream specifically refers to using a "length" tag to tell GNU Radio blocks how long a specific chunk of samples is. This can be useful when doing packet processing, where the number of samples to be used is known. The GNU Radio scheduler can use these "length" tags to ensure an entire packet's worth of data is available to a GNU Radio block at once, instead of forcing the block developer to include buffering logic in their code. GNU Radio refers to a single chunk of related data as a Protocol Data Unit, or PDU. The official Tagged Stream documentation can be found [here](https://gnuradio.org/doc/doxygen/page_tagged_stream_blocks.html).

The Environment simulator supports the use of Tagged Streams for timed bursts. To use this capability, you must specify which string the env_sink block should be looking for to denote the length of the next PDU to be transmitted. Set the "tx_pkt_len_name" parameter in the env_sink to whatever string your radio application uses to denote your PDU length. A commonly used string for this purpose is simply "tx_pkt_len".

If using Tagged Streams for timed bursts, you must include your "tx_pkt_len" tag and a "tx_time" tag on the first sample of a tx burst. If your first "tx_pkt_len" tag has an offset of 0, and your packet length is 1000 items, your next "tx_pkt_len" and "tx_time" tags must appear with an offset of 1000. TX bursts should not overlap, and there should not be gaps in samples between bursts.

#### tx_pkt_len

* **offset**: sample number associated with the start of a burst. The offset for a tx_pkt_len tag must occur immediately after the end of the previous PDU.

* **key**: PMT encoded string "tx_pkt_len", or whatever string you provided in the "tx_pkt_len_name" parameter of the env_sink block in your radio application.

* **value**: PMT encoded integer. This is the length of your PDU in items (ie samples) not bytes.

#### tx_time

* **offset**: sample number associated with the start of a burst. tx_time tags must occur on the same sample number as a tx_sob tag.

* **key**: PMT encoded string "tx_time"

* **value**: PMT encoded tuple of values. The first item in the pair is the PMT encoded uint64 epoch time (wall time). The second item in the pair is the PMT encoded double fractional epoch time. An epoch timestamp of 1416299676.3453495 would appear as (1416299676, 0.3453495).


## Adding Stream Tags from C++
You can add stream tags to an output sample stream from inside a GNU Radio block using member functions inherited from gr::block. You have the option of first initializing a tag_t object and submitting that or simply specifying all of the fields used in a stream tag.

The following function call, when used in your GNU Radio block, will allow you to add a stream tag on the specified output by specifying all of the fields that make up a stream tag. Block outputs are zero based, so for the common case of a block with only one output, "which_output" will be 0.
"srcid" is optional. Remember, you must specify parameters as PMTs, using pmt::pmt_string_to_symbol or pmt::intern methods to convert strings to PMTs, pmt::from_double for double types, and so on and so fort. Check the PMT documentation for a full list of conversion functions.

```C++
void gr::block::add_item_tag(unsigned int       which_output,
                             uint64_t           abs_offset,
                             const pmt::pmt_t & key,
                             const pmt::pmt_t & value,
                             const pmt::pmt_t & srcid = pmt::PMT_F)
```

The following function call will let you add a stream tag if you already have initialized a tag_t object.

```C++
void gr::block::add_item_tag(unsigned int  which_output,
                             uint64_t      abs_offset,
                             const tag_t & tag)
```

You'll generally call one of these two functions inside your work or general_work function.


## Adding Stream Tags from Python
GNU Radio provides a Python API reference for using Stream Tags. See the "Using Stream Tags" section [here](https://gnuradio.org/doc/doxygen/page_python_blocks.html)

See below for an example of adding stream tags from within a GNU Radio block written in Python:

```python
def work(self, input_items, output_items):

    ....

    add_item_tag(which_output, abs_offset, key, value, srcid)

    ....
```

Note that which_output is still a zero based integer, abs_offset is still the integer absolute sample offset for the stream tag, and key, value, srcid are all PMT types. You can use either the data-type specific PMT conversion functions to go from Python data types to PMTs or use pmt.to_pmt() to automatically convert Python data types to a PMT. You must import the pmt module to use these functions.