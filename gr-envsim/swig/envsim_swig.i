/* -*- c++ -*- */

#define ENVSIM_API

%include <std_vector.i>
%include "gnuradio.i"			// the common stuff

//load generated python docstrings
%include "envsim_swig_doc.i"

////////////////////////////////////////////////////////////////////////
// SWIG should not see the uhd::usrp::multi_usrp class
////////////////////////////////////////////////////////////////////////
%ignore gr::uhd::usrp_sink::get_device;
%ignore gr::uhd::usrp_source::get_device;

%{
#include "envsim/envsim_source.h"
#include "envsim/socket_meta_pdu.h"
#include "envsim/env_sink.h"
#include "envsim/env_source.h"
#include "envsim/tx_time_tagger.h"
#include "envsim/zmq_envsim_source.h"
%}

%include "envsim/env_block.h"

////////////////////////////////////////////////////////////////////////
// used types
////////////////////////////////////////////////////////////////////////

// warning!!!! implies we're on 64 bit system
typedef long long time_t;

%template(uhd_string_vector_t) std::vector<std::string>;

%template(uhd_size_vector_t) std::vector<size_t>;

%include <uhd/config.hpp>

%include <uhd/utils/pimpl.hpp>

%ignore uhd::dict::operator[]; //ignore warnings about %extend
%include <uhd/types/dict.hpp>
%template(string_string_dict_t) uhd::dict<std::string, std::string>; //define after dict

%extend uhd::dict<std::string, std::string>{
    std::string __getitem__(std::string key) {return (*self)[key];}
    void __setitem__(std::string key, std::string val) {(*self)[key] = val;}
};

%include <uhd/types/device_addr.hpp>

%include <uhd/types/io_type.hpp>

%template(range_vector_t) std::vector<uhd::range_t>; //define before range
%include <uhd/types/ranges.hpp>

%include <uhd/types/tune_request.hpp>

%include <uhd/types/tune_result.hpp>

%include <uhd/types/io_type.hpp>

%include <uhd/types/time_spec.hpp>

%extend uhd::time_spec_t{
    uhd::time_spec_t __add__(const uhd::time_spec_t &what)
    {
        uhd::time_spec_t temp = *self;
        temp += what;
        return temp;
    }
    uhd::time_spec_t __sub__(const uhd::time_spec_t &what)
    {
        uhd::time_spec_t temp = *self;
        temp -= what;
        return temp;
    }
};

%include <uhd/types/stream_cmd.hpp>

%include <uhd/types/clock_config.hpp>

%include <uhd/types/metadata.hpp>

%template(device_addr_vector_t) std::vector<uhd::device_addr_t>;

%include <uhd/types/sensors.hpp>

%include <uhd/stream.hpp>


%include "envsim/envsim_source.h"
GR_SWIG_BLOCK_MAGIC2(envsim, envsim_source);

%include "envsim/socket_meta_pdu.h"
GR_SWIG_BLOCK_MAGIC2(envsim, socket_meta_pdu);

%include "envsim/env_sink.h"
GR_SWIG_BLOCK_MAGIC2(envsim, env_sink);

%include "envsim/env_source.h"
GR_SWIG_BLOCK_MAGIC2(envsim, env_source);


%include "envsim/tx_time_tagger.h"
GR_SWIG_BLOCK_MAGIC2(envsim, tx_time_tagger);
%include "envsim/zmq_envsim_source.h"
GR_SWIG_BLOCK_MAGIC2(envsim, zmq_envsim_source);
