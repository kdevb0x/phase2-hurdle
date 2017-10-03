#!/usr/bin/env python
# encoding: utf-8

from itertools import izip
import logging
import logging.config
import os
import random
import signal
import socket
import struct
import sys
import time

import zmq


import registration_pb2 as reg
import collaboration_pb2 as collab

from argparse import ArgumentParser
from argparse import ArgumentDefaultsHelpFormatter

LOG_LEVELS = {"DEBUG":logging.DEBUG, 
              "INFO":logging.INFO, 
              "WARNING":logging.WARNING, 
              "ERROR":logging.ERROR, 
              "CRITICAL":logging.CRITICAL}

def ip_int_to_string(ip_int):
    '''
    Convert integer formatted IP to IP string
    '''
    return socket.inet_ntoa(struct.pack('!L',ip_int))


def get_all_subfields(msg_descriptor, prefix_name="", prefix_num="",
                      current_depth=0, max_depth=None):
    '''
    Recursively traverse all messages starting with the provided top level descriptor
    and return a list of message names and a list of message IDs.
    
    The message name list is formatted as a list of strings like:
        "top_level_message_name.sub_message_name.sub_sub_message_name"
    The message ID list is formatted as a list of strings like:
        "top_level_message_id.sub_message_id.sub_sub_message_id"
    '''

    # keep going until we hit the max specified recursion depth
    if max_depth is not None and current_depth >= max_depth:
        return [], []

    # get all the fields in the current message
    msg_fields = msg_descriptor.fields
    names_list = []
    ids_list = []

    # loop through each field in the current message, append the name and ID
    # to the relevant lists, and recursively check for submessages
    for mf in msg_fields:
        full_name = "{}.{}".format(prefix_name, mf.name)
        full_num = "{}.{}".format(prefix_num, mf.number)
        
        names_list.append(full_name)
        ids_list.append(full_num)
        
        #print "{} \t {}".format(full_name, full_num)
        # check for submessages
        submsg_descriptor = mf.message_type

        # if there are submessages, process them
        if submsg_descriptor:
            subnames, sub_ids = get_all_subfields(submsg_descriptor,
                                                  full_name,
                                                  full_num,
                                                  current_depth+1, 
                                                  max_depth)

            # append the submessage info to our tracking list
            names_list.extend(subnames)
            ids_list.extend(sub_ids)

    return names_list, ids_list

def make_message_name_to_id_map(top_level_message_descriptor, top_level_message_name):
    '''
    Make a dict whose keys are message names and values are message IDs, pulled
    automatically from the compiled protocol buffer file
    '''

    # get the list of message names and message IDs
    names_list, ids_list = get_all_subfields(msg_descriptor=top_level_message_descriptor,
                                             prefix_name=top_level_message_name,
                                             prefix_num="0")

    msg_id_map = {}

    # add each message to the message map
    for msg_name, msg_id in izip(names_list, ids_list):
        msg_id_map[msg_name] = msg_id

    return msg_id_map


def make_my_supported_message_ids(msg_map):
    '''
    Define a list of supported message IDs for use in the Hello message
    '''

    # Note that this does not support all fields in the informational declaration message

    # using the mapping of names to message IDs for readability's sake
    supported_msg_ids = [msg_map["collaborate.hello"],
                         msg_map["collaborate.hello.my_dialect"],
                         msg_map["collaborate.hello.my_network_id"],
                         msg_map["collaborate.informational_declaration"],
                         msg_map["collaborate.informational_declaration.statement_id"],
                         msg_map["collaborate.informational_declaration.my_network_id"],
                         msg_map["collaborate.informational_declaration.performance"],
                         msg_map["collaborate.informational_declaration.performance.scalar_performance"],
                        ]
    return supported_msg_ids

def parse_args(argv):
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    # Setup argument parser                                              ArgumentDefaultsHelpFormatter
    parser = ArgumentParser( formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("--server-ip", default="127.0.0.1", help="IP address of Collaboration Server")
    parser.add_argument("--server-port", default=5556, type=int, help="Port the server is listening on")
    parser.add_argument("--client-ip", default="127.0.0.1", help="IP address this client is listening on")
    parser.add_argument("--client-port", default=5557, type=int, help="Port the client listens to for messages from the server")
    parser.add_argument("--peer-port", default=5558, type=int, help="Port the client listens to for peer-to-peer messages")
    parser.add_argument("--message-timeout", default=5.0, type=float, help="Timeout for messages sent to the server or peers")
    parser.add_argument("--log-config-filename", default="collab_client_logging.conf",
                        help="Config file for logging module")

    
    # Process arguments
    args = vars(parser.parse_args())
    
    return args

class CollabClient(object):
    '''
    Top level object that runs a very simplistic client. This is not likely to be performant
    for any appreciable amount of messaging traffic. This code is an example of how to
    interact with the server and parse peer messages, but use at your own risk if this is
     included in competition code
    '''

    def __init__(self, server_host="127.0.0.1", server_port=5556,
                       client_host="127.0.0.1", client_port=5557, 
                       peer_port=5558, message_timeout=5.0,
                       log_config_filename="logging.conf"):


        # set up logging
        logging.config.fileConfig(log_config_filename)
        self.log = logging.getLogger("collab_client")
        
        self.server_host = server_host
        self.server_port = server_port
        self.client_host = client_host
        self.client_port = client_port
        self.peer_port = peer_port    

        # convert IP address from string to packed bytes representation
        self.client_ip_bytes = struct.unpack('!L',socket.inet_aton(self.client_host))[0]

        self.max_keepalive = None

        # being late is expensive so building in a buffer.
        # we multiply our computed initial keepalive timer value by this scale factor
        # to build in some margin in our reply time
        self.keepalive_safety_margin = 0.75 
        self.keepalive_counter = None

        self.my_nonce = None


        # initialize a statement id counter
        self.statement_counter = 1

        self.peers = {}

        # This sets up a handler for each type of server message I support
        self.server_msg_handlers = {
                                    "inform":self.handle_inform,
                                    "notify":self.handle_notify,
                                   }

        # This sets up a handler for each top level peer message I support
        self.peer_msg_handlers = {
                                    "hello":self.handle_hello,
                                    "informational_declaration":self.handle_informational_declaration,
                                    }

        # This sets up a handler for each Declaration message type I support
        self.declaration_handlers = {"performance":self.handle_performance}

        # This sets up a handler for each Performance message type I support
        self.performance_handlers = {"scalar_performance":self.handle_scalar_performance}

        # This controls how long the client will try to send messages to other endpoints before
        # throwing a warning and giving up
        self.message_timeout = float(message_timeout)

        # initialize my message ID map used for readability
        self.msg_map = make_message_name_to_id_map(collab.Collaborate.DESCRIPTOR,
                                                   "collaborate")

        # store of the list of message IDs I support
        self.my_supported_msg_ids = make_my_supported_message_ids(self.msg_map)

    def setup(self):
        '''
        Set up initial zeromq connections.

        The client needs to start up its main listener for incoming messages from the server 
        and a separate socket to handle messages coming from peers. It will also set up a
        poller for both sockets to allow it to service server and peer connections without
        blocking
        '''

        self.z_context = zmq.Context()
        self.poller = zmq.Poller()

        # initialize the listening socket for the server
        self.listen_socket = self.z_context.socket(zmq.PULL)
        self.poller.register(self.listen_socket, zmq.POLLIN)

        
        self.listen_socket.bind("tcp://%s:%s" % (self.client_host,self.client_port))
        self.log.info("Collaboration client listening on host %s and port %i", 
                      self.client_host, self.client_port)

        # initialize the listening socket for peers
        self.peer_pull_socket = self.z_context.socket(zmq.PULL)
        self.poller.register(self.peer_pull_socket, zmq.POLLIN)
        self.peer_pull_socket.bind("tcp://%s:%s" % (self.client_host,self.peer_port))
        self.log.info("Collaboration client listening for peers on host %s and port %i", 
                      self.client_host, self.peer_port)

        self.log.info("Connecting to server on host %s and port %i",
                       self.server_host, self.server_port)

        # initialize the push socket for sending registration and heartbeat messages to
        # the server
        self.server_socket = self.z_context.socket(zmq.PUSH)
        self.poller.register(self.server_socket, zmq.POLLOUT)
        self.server_socket.connect("tcp://%s:%i" % (self.server_host, self.server_port))


        self.log.debug("Connected to server")

    def teardown(self):
        '''
        Close out zeroMQ connections and zeroMQ context cleanly
        '''

        self.log.debug("Shutting down sockets")

        # unregister from the poller and close the server listening socket
        self.poller.unregister(self.listen_socket)
        self.listen_socket.close()

        # unregister from the poller and close the server push socket
        self.poller.unregister(self.server_socket)
        self.server_socket.close()

        # unregister from the poller and close the peer listening socket
        self.poller.unregister(self.peer_pull_socket)
        self.peer_pull_socket.close()

        # cleanup any resources allocated for each peer
        peer_id_list = self.peers.keys()
        for peer_id in peer_id_list:
            self.cleanup_peer(peer_id)

        self.z_context.term()

        self.log.info("shutdown complete")

    def send_with_timeout(self, sock, message, timeout):
        '''
        Try to send a message with some timeout to prevent a single endpoint from
        makeing me wait forever on a response
        '''
        tick = time.time()

        tock = time.time()

        success = False

        # check if an endpoint is open and ready to accept a message. If the endpoint
        # is ready, send the message. If we reach the timeout before an endpoint appears to be
        # ready, give up on the message and log an error
        while tock-tick < timeout and success == False:

            self.log.debug("Trying to send message")
            socks = dict(self.poller.poll())   
        
            if sock in socks and socks[sock] == zmq.POLLOUT:
                self.log.debug("Socket ready, sending")
                sock.send(message.SerializeToString())
                success = True
            else:
                self.log.warn("Tried to send message, endpoint is not connected. Retrying")
                time.sleep(1)
                tock=time.time()

        if not success:
            self.log.error("Could not send message after %f seconds", timeout)
        else:
            self.log.debug("Message sent")

        return

    def list_peers(self):
        '''
        Generate a list of peers I know about
        '''
        peer_addresses = [val["ip_address"] for key, val in self.peers.items()]

        return peer_addresses


    def add_peer(self, ip):
        '''
        I've been informed of a new peer. Add it to the list of peers I'm tracking
        '''
        self.log.info("adding peer %i", ip)
        

        ip_string = ip_int_to_string(ip)

        self.log.debug("trying to connect to peer at IP: %s and port %i",
                       ip_string, self.client_port)

        # create a socket for my new peer
        peer_socket = self.z_context.socket(zmq.PUSH)
        peer_socket.connect("tcp://%s:%i" % (ip_string,self.peer_port))

        # add socket to poller
        self.poller.register(peer_socket, zmq.POLLOUT)

        # store off new peer
        self.peers[ip] = {"ip_address":ip,
                          "ip_string":ip_string,
                          "socket":peer_socket}

        peer_addresses = self.list_peers()

        self.log.debug("list of peers: %s",peer_addresses)

        # send a Hello message to the new client
        self.send_hello(self.peers[ip])      

        return

    def cleanup_peer(self, ip):
        '''
        Releae any resources allocated for the peer associated with the given IP
        '''

        # close socket to old peer
        peer_socket = self.peers[ip]["socket"]
        self.poller.unregister(peer_socket)

        peer_socket.setsockopt(zmq.LINGER, 0)
        peer_socket.close()

        self.log.info("Removing peer %s", ip_int_to_string(ip))

        del self.peers[ip]

        return


    def handle_inform(self, message):
        '''
        I received an inform message. Set up my keepalive timer and store off the peers
        '''
        self.log.info("Received Inform message")

        inform = message.inform

        # store off the nonce and max keepalive timer value the server told me
        self.my_nonce = inform.client_nonce
        self.max_keepalive = inform.keepalive_seconds

        # store off my neighbor contact info
        neighbors = inform.neighbors
        
        self.log.debug("Inform message contents: %s", message)
        for n in neighbors:
            if n != self.client_ip_bytes:
                self.add_peer(n)

        return


    def handle_notify(self, message):
        '''
        The server has given me an update on my peers list. Handle these updates
        '''
        self.log.info("Received Notify message")

        neighbors = message.notify.neighbors
        # find new peers

        # check list for new peers. Do initial setup required for any new peers
        for n in neighbors:
            if n not in self.peers and n != self.client_ip_bytes:
                self.add_peer(n)

        # stop tracking peers that have left
        current_peers = self.peers.keys()

        for p in current_peers:
            if p not in neighbors:
                self.cleanup_peer(p)
        return

    def handle_hello(self, message):
        '''
        I've received a hello message from a peer. Right now this only prints the message
        '''
        self.log.info("Received Hello message from peer %i",message.hello.my_network_id)
        self.log.debug("Hello Full Contents: %s",message.hello)
        return


    def handle_informational_declaration(self, message):
        '''
        I've received a declaration from my peer. This doesn't do much right now
        '''
        statement_id = message.informational_declaration.statement_id
        network_id = message.informational_declaration.my_network_id
        
        self.log.info("Received declaration message id %i from peer %s",
                      statement_id, ip_int_to_string(network_id))

        self.log.debug("Message full contents: %s", message)

        declaration = message.informational_declaration

        try:
            
            # this is a simple way to handle declarations that does not account
            # for any associations
            if len(declaration.demand) > 0:
                self.log.warn("Demand messages not implemented")
                
            if len(declaration.resource) > 0:
                self.log.warn("Resource messages not implemented")
                
            if len(declaration.performance) > 0:
                handler = self.declaration_handlers["performance"]
                for p in declaration.performance:
                    handler(p)
                   
            if len(declaration.observation) > 0:
                self.log.warn("Observation messages not implemented")

        except KeyError as err:
            self.log.warn("received unknown message type %s", err)


    def handle_performance(self, performance):
        '''
        Message handler for Performance messages
        '''
        self.log.debug("Declaration message was a Performance message")

        try:
            handler = self.performance_handlers[performance.WhichOneof("payload")]
            handler(performance)

        except KeyError as err:
            self.log.warn("received unknown message type %s", err)

    def handle_scalar_performance(self, performance):
        '''
        Message handler for Scalar Performance messages
        '''
        self.log.debug("Performance message was a Scalar Performance message")
        self.log.info("Scalar performance was %f",performance.scalar_performance)

    def send_register(self):
        '''
        Generate a register message and send it to the collaboration server
        '''

        self.log.info("sending register message to server")

        # construct message to send to server
        message = reg.TalkToServer()
        message.register.my_ip_address = self.client_ip_bytes

        self.log.debug("register message contents: %s", message)

        # serialize and send message to server
        self.send_with_timeout(sock=self.server_socket, 
                               message=message, 
                               timeout=self.message_timeout)

    def send_keepalive(self):
        '''
        Generate a keepalive message and send it to the collaboration server
        '''

        self.log.info("sending keepalive")

        # construct message to send to server
        message = reg.TalkToServer()
        message.keepalive.my_nonce = self.my_nonce

        self.log.debug("keepalive message contents: %s", message)

        # serialize and send message to server
        self.send_with_timeout(sock=self.server_socket, 
                               message=message, 
                               timeout=self.message_timeout)


    def send_leave(self):
        '''
        Be polite and tell everyone that we are leaving the collaboration network
        '''
        self.log.info("sending leave message")

        # construct message to send to server
        message = reg.TalkToServer()
        message.leave.my_nonce = self.my_nonce

        self.log.debug("leave message contents: %s", message)
        
        # serialize and send message to server
        self.send_with_timeout(sock=self.server_socket, 
                               message=message, 
                               timeout=self.message_timeout)

    def send_hello(self, peer):
        '''
        Send a hello message to my peer
        '''
        self.log.info("sending hello message to peer %s", peer["ip_string"])

        # Create the top level Collaborate message wrapper
        message = collab.Collaborate()

        # add to the supported declaration and performance lists using the extend()
        # method
        message.hello.my_dialect.extend(self.my_supported_msg_ids)

        # set my network ID to my IP address (on the collaboration protocol network)
        message.hello.my_network_id = self.client_ip_bytes

        self.log.debug("Hello message contents: %s", message)

        # serialize and send message to peer
        self.send_with_timeout(sock=peer["socket"], 
                               message=message, 
                               timeout=self.message_timeout)

    def send_performance(self, peer, scalar_performance):
        '''
        Send a scalar performance declaration to my peer
        '''
        self.log.info("sending performance to peer %s", peer["ip_string"])

        message = collab.Collaborate()
        message.informational_declaration.statement_id = self.statement_counter
        message.informational_declaration.my_network_id = self.client_ip_bytes


        # create a new performance object in the informational_declaration performance list
        # and update it with a new value using the add() method
        performance = message.informational_declaration.performance.add()
        performance.scalar_performance = scalar_performance

        self.log.debug("Performance message contents: %s", message)
        
        # increment the statement counter
        self.statement_counter = self.statement_counter + 1

        # serialize and send message to peer
        self.send_with_timeout(sock=peer["socket"],
                               message=message, 
                               timeout=self.message_timeout)

    def manage_keepalives(self):
        '''
        Keep track of my keepalive counter and ensure I send a new keepalive message to the
        server with some random counter and a safety margin to make sure the server isn't
        hit by too many keepalive messages simultaneously and also to ensure I'm not late
        '''
        tock = time.time()
        elapsed_time = tock - self.tick


        # is it time to send the keepalive?
        if elapsed_time >= self.keepalive_counter:
            self.tick = tock
            
            self.send_keepalive()
                        
            # picking a new keepalive counter at random so the server is
            # less likely to get bogged down by a bunch of requests at once.
            new_count = random.random()*self.max_keepalive
            
            # building in a fudge factor so we'll always be well below the max
            # timeout
            self.keepalive_counter = new_count * self.keepalive_safety_margin
            self.log.debug("starting new keepalive timer of %f seconds",
                           self.keepalive_counter)

        return


    def run(self):
        '''
        Run the client's event loop.
        This is not expected to keep up with high update rates, only as an example of how
        to send messages and handle messages sent to me
        '''
        self.tick = time.time()

        self.log.info("Sending register message")
        self.send_register()

        last_performance_update = 0

        # arbitrarily chosen update period
        performance_update_period = 20

        while True:

            # manage the keepalive counter. Don't bother until the server
            # tells us what the keepalive max should be
            if self.max_keepalive is not None:
                self.manage_keepalives()


            socks = dict(self.poller.poll())
            
            
            if time.time() - last_performance_update > performance_update_period:
                # if it's time to send out a performance update, check if there
                # are any peers. If so, pick one at random and send it an update.
                if len(self.peers) > 0:
                    
                    scalar_performance = random.random() 
                    
                    peer_id = random.choice(self.peers.keys())
                    self.send_performance(self.peers[peer_id], scalar_performance)
                    last_performance_update = time.time()
            
            # look for a new message from either a peer or the server
            # Polling may not be that efficient, but this is an example of using
            # the code and talking to the server and peers. This is not intended
            # to be a competition ready client.
            if self.listen_socket in socks:

                self.log.debug("processing message from server")

                # get a message off the server listening socket and deserialize it
                raw_message = self.listen_socket.recv()
                message = reg.TellClient.FromString(raw_message)

                self.log.debug("message was %s", message)

                # find and run the appropriate handler
                try:
                    handler = self.server_msg_handlers[message.WhichOneof("payload")]
                    handler(message)

                except KeyError as err:
                    self.log.error("received unsupported message type %s", err)

            # check for new messages from my peers
            elif self.peer_pull_socket in socks:

                self.log.debug("processing message from peer")

                # get a message off the peer listening socket and deserialize it
                raw_message = self.peer_pull_socket.recv()
                message = collab.Collaborate.FromString(raw_message)

                self.log.debug("message was %s", message)

                # find and run the appropriate handler
                try:
                    handler = self.peer_msg_handlers[message.WhichOneof("payload")]
                    handler(message)

                except KeyError as err:
                    self.log.warn("received unhandled message type %s", err)

            else:
                time.sleep(0.5)


def handle_sigterm(signal, frame):
    '''
    Catch SIGTERM and signal the script to exit gracefully
    '''
    raise KeyboardInterrupt


def main(argv=None):

    print("Collaboration Client starting, CTRL-C to exit")    

    # parse command line args
    args = parse_args(argv)
        
    collab_client = CollabClient(server_host=args["server_ip"], server_port=args["server_port"],
                                 client_host=args["client_ip"], client_port=args["client_port"],
                                 peer_port=args["peer_port"],
                                 log_config_filename=args["log_config_filename"])


    collab_client.setup()


    try:
        collab_client.run()
    except KeyboardInterrupt:
        print("interrupt received, stopping...")
        
        try:
            collab_client.send_leave()
        except TypeError as err:
            print("error while shutting down:", err)

        collab_client.teardown()


if __name__ == "__main__":

    main()
