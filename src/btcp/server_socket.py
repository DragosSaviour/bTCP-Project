from btcp.btcp_socket import BTCPSocket, BTCPStates
from btcp.lossy_layer import LossyLayer
from btcp.constants import *
import struct
import queue
import random
import time


class BTCPServerSocket(BTCPSocket):

    """bTCP server socket
    A server application makes use of the services provided by bTCP by calling
    accept, recv, and close.

    You're implementing the transport layer, exposing it to the application
    layer as a (variation on) socket API. Do note, however, that this socket
    as presented is *always* in "listening" state, and handles the client's
    connection in the same socket. You do not have to implement a separate
    listen socket. If you get everything working, you may do so for some extra
    credit.

    To implement the transport layer, you also need to interface with the
    network (lossy) layer. This happens by both calling into it
    (LossyLayer.send_segment) and providing callbacks for it
    (BTCPServerSocket.lossy_layer_segment_received, lossy_layer_tick).

    Your implementation will operate in two threads, the network thread,
    where the lossy layer "lives" and where your callbacks will be called from,
    and the application thread, where the application calls connect, send, etc.
    This means you will need some thread-safe information passing between
    network thread and application thread.
    Writing a boolean or enum attribute in one thread and reading it in a loop
    in another thread should be sufficient to signal state changes.
    Lists, however, are not thread safe, so to pass data and segments around
    you probably want to use Queues, or a similar thread safe collection.
    """


    def __init__(self, window, timeout):
        """Constructor for the bTCP server socket. Allocates local resources
        and starts an instance of the Lossy Layer.

        You can extend this method if you need additional attributes to be
        initialized, but do *not* call accept from here.
        """
        super().__init__(window, timeout)
        self._lossy_layer = LossyLayer(self, SERVER_IP, SERVER_PORT, CLIENT_IP, CLIENT_PORT)
        self.s_queue = queue.Queue(maxsize=window)
        self.s_syn = 0
        self.s_ack = 0
        self.establishing_ack = 0
        self.closing_ack = 0
        


    ###########################################################################
    ### The following section is the interface between the transport layer  ###
    ### and the lossy (network) layer. When a segment arrives, the lossy    ###
    ### layer will call the lossy_layer_segment_received method "from the   ###
    ### network thread". In that method you should handle the checking of   ###
    ### the segment, and take other actions that should be taken upon its   ###
    ### arrival, like acknowledging the segment and making the data         ###
    ### available for the application thread that calls to recv can return  ###
    ### the data.                                                           ###
    ###                                                                     ###
    ### Of course you can implement this using any helper methods you want  ###
    ### to add.                                                             ###
    ###                                                                     ###
    ### Since the implementation is inherently multi-threaded, you should   ###
    ### use a Queue, not a List, to transfer the data to the application    ###
    ### layer thread: Queues are inherently threadsafe, Lists are not.      ###
    ###########################################################################

    ############## Helper Functions ##################
    def pack_and_pad(payload):  
        # Pad the payload so it has length 1008. Then pack it into bytes.
        input_value = b'\0'
        padding_length = 1008 - len(payload) 
        payload = payload + (input_value * padding_length)
        return struct.pack("!1008s", payload)


    def increment_synack(syn):
        # Ensure syn is never out of bounds and never 0, since we use that as a boolean
        if syn < 65535:     return syn + 1
        else:               return 1


    ###################################################
    

    def lossy_layer_segment_received(self, segment):
        """Called by the lossy layer whenever a segment arrives.

        Things you should expect to handle here (or in helper methods called
        from here):
            - checksum verification (and deciding what to do if it fails)
            - receiving syn and client's ack during handshake
            - receiving segments and sending acknowledgements for them,
              making data from those segments available to application layer
            - receiving fin and client's ack during termination
            - any other handling of the header received from the client

        Remember, we expect you to implement this *as a state machine!*
        """
        # Checksum verification. If it fails the segment is dropped (return)
        acc = sum(x for (x,) in struct.iter_unpack(R'!H', segment))
        while acc > 0xFFFF:
            carry = acc >> 16
            acc &= 0xFFFF
            acc += carry
        if acc != 0xFFFF: return

        # Divide the header and payload
        header_length = 10
        header = segment[:header_length]
        payload = segment[header_length:]

        # Unpack the header
        seqnum, acknum, syn_set, ack_set, fin_set, window, length, checksum = unpack_segment_header(header)

        # Connection establishment
        if syn_set and (self._state == BTCPStates.ACCEPTING or self._state == BTCPStates.SYN_RCVD):
            self.s_ack = seqnum                                 # Remember sequence number of client
            self._state = BTCPStates.SYN_RCVD                   # Set state to SYN_RCVD
            return
        if ack_set and self._state == SYN_RCVD and acknum == self.establishing_ack and (self.s_ack + 1) == seqnum:
            self.s_ack = increment_synack(self.s_ack)
            self._state = BTCPStates.ESTABLISHED
            return
                    
        # Connection termination
        # Missing a timeout
        if fin_set and (self._state == BTCPStates.ESTABLISHED or self._state == BTCPStates.CLOSING):
            self._state = BTCPStates.CLOSING                    # Set state to CLOSING
            if self.closing_ack == 0:
                self.s_syn = increment_synack(self.s_syn)          # Increment sequence number (if we haven't sent an ack before)
            header = build_segment_header(self.s_syn, seqnum, ack_set=True, fin_set=True)
            segment = header + pack_and_pad(b'')
            self._lossy_layer.send_segment(self._lossy_layer, segment) # Sent ack & fin
            if self.closing_ack == 0:
                self.closing_ack = self.s_syn                   # Remember sequence number
            return
        if ack_set and self._state == CLOSING and acknum == self.closing_ack:
            self._state = BTCPStates.CLOSED
            self._lossy_layer.__del__(self._lossy_layer)
            return

        # Processing segments during establishment
        if not ack_set and not syn_set and not fin_set and self._state == BTCPStates.ESTABLISHED:
            if (self.s_ack + 1 == seqnum):  # if next expected segment put it in queue and increment syn
                self.s_syn = increment_synack(self.s_syn)
                self.s_ack = increment_synack(self.s_ack)
                self.s_queue.put(payload)
            window = max(1, self._window - len(self.s_queue))
            # 
            header = build_segment_header(self.s_syn, self.s_ack, window=window)
            segment = header + pack_and_pad(b'')
            self._lossy_layer.send_segment(self._lossy_layer, segment)
            return


    def lossy_layer_tick(self):
        """Called by the lossy layer whenever no segment has arrived for
        TIMER_TICK milliseconds. Defaults to 100ms, can be set in constants.py.

        NOTE: Will NOT be called if segments are arriving; do not rely on
        simply counting calls to this method for an accurate timeout. If 10
        segments arrive, each 99 ms apart, this method will NOT be called for
        over a second!

        The primary use for this method is to be able to do things in the
        "network thread" even while no segments are arriving -- which would
        otherwise trigger a call to lossy_layer_segment_received. On the server
        side, you may find you have no actual need for this method. Or maybe
        you do. See if it suits your implementation.

        You will probably see some code duplication of code that doesn't handle
        the incoming segment among lossy_layer_segment_received and
        lossy_layer_tick. That kind of duplicated code would be a good
        candidate to put in a helper method which can be called from either
        lossy_layer_segment_received or lossy_layer_tick.
        """
        pass # present to be able to remove the NotImplementedError without having to implement anything yet.
        raise NotImplementedError("No implementation of lossy_layer_tick present. Read the comments & code of server_socket.py.")


    ###########################################################################
    ### You're also building the socket API for the applications to use.    ###
    ### The following section is the interface between the application      ###
    ### layer and the transport layer. Applications call these methods to   ###
    ### accept connections, receive data, etc. Conceptually, this happens   ###
    ### in "the application thread".                                        ###
    ###                                                                     ###
    ### You *can*, from this application thread, send segments into the     ###
    ### lossy layer, i.e. you can call LossyLayer.send_segment(segment)     ###
    ### from these methods without ensuring that happens in the network     ###
    ### thread. However, if you do want to do this from the network thread, ###
    ### you should use the lossy_layer_tick() method above to ensure that   ###
    ### segments can be sent out even if no segments arrive to trigger the  ###
    ### call to lossy_layer_input. When passing segments between the        ###
    ### application thread and the network thread, remember to use a Queue  ###
    ### for its inherent thread safety. Whether you need to send segments   ###
    ### from the application thread into the lossy layer is up to you; you  ###
    ### may find you can handle all receiving *and* sending of segments in  ###
    ### the lossy_layer_segment_received method.                            ###
    ###                                                                     ###
    ### Note that because this is the server socket, and our (initial)      ###
    ### implementation of bTCP is one-way reliable data transfer, there is  ###
    ### no send() method available to the applications. You should still    ###
    ### be able to send segments on the lossy layer, however, because       ###
    ### of acknowledgements and synchronization. You should implement that  ###
    ### above.                                                              ###
    ###########################################################################

    def send_SYNACK():
        window = max(1, self._window - len(self.s_queue))
        header = build_segment_header(self.s_syn, self.s_ack, syn_set=True, ack_set=True, window=window)
        segment = header + pack_and_pad(b'')
        self._lossy_layer.send_segment(self._lossy_layer, segment)
        return


    def accept(self):
        """Accept and perform the bTCP three-way handshake to establish a
        connection.

        accept should *block* (i.e. not return) until a connection has been
        successfully established (or some timeout is reached, if you want. Feel
        free to add a timeout to the arguments). You will need some
        coordination between the application thread and the network thread for
        this, because the syn and final ack from the client will be received in
        the network thread.

        Hint: assigning to a boolean or enum attribute in thread A and reading
        it in a loop in thread B (preferably with a short sleep to avoid
        wasting a lot of CPU time) ensures that thread B will wait until the
        boolean or enum has the expected value. We do not think you will need
        more advanced thread synchronization in this project.
        """
        timeout = 0
        while(True):
            if self.s_syn == 0:
                self.s_syn = random.randint(1,65535)        # Generate Server's sequence number
            self.establishing_ack = self.s_syn              # Remember sequence number
            self._state = BTCPStates.ACCEPTING              

            # ACCEPTING -> SYN_RCVD
            while self._state != BTCPStates.SYN_RCVD:
                time.sleep(10)
                timeout += 10
                if timeout > 5000:
                    self._state = BTCPStates.CLOSED
                    break
            send_SYNACK()
            
            # SYN_RCVD -> ESTABLISHED
            retries = 0
            timer = 0
            time.sleep(10)
            while self._state != BTCPStates.ESTABLISHED and retries < 20 and timer < 250:
                send_SYNACK()
                retries += 1
                timer += 10
                time.sleep(10)
            if self._state == BTCPStates.ESTABLISHED:
                break
            


    def recv(self):
        """Return data that was received from the client to the application in
        a reliable way.

        If no data is available to return to the application, this method
        should block waiting for more data to arrive. If the connection has
        been terminated, this method should return with no data (e.g. an empty
        bytes b'').

        If you want, you can add an argument to this method stating how many
        bytes you want to receive in one go at the most (but this is not
        required for this project).

        You are free to implement this however you like, but the following
        explanation may help to understand how sockets *usually* behave and you
        may choose to follow this concept as well:

        The way this usually works is that "recv" operates on a "receive
        buffer". Once data has been successfully received and acknowledged by
        the transport layer, it is put "in the receive buffer". A call to recv
        will simply return data already in the receive buffer to the
        application.  If no data is available at all, the method will block
        until at least *some* data can be returned.
        The actual receiving of the data, i.e. reading the segments, sending
        acknowledgements for them, reordering them, etc., happens *outside* of
        the recv method (e.g. in the network thread).
        Because of this blocking behaviour, an *empty* result from recv signals
        that the connection has been terminated.

        Again, you should feel free to deviate from how this usually works.
        """
        # wait for data
        while(self.s_queue.empty() and self._state == BTCPStates.ESTABLISHED):
            time.sleep(100)

        # Get data from the queue
        # If connection has been terminated and queue is empty returns empty byte
        data = b''
        data_segments = 0
        while(data_segments <= 25): # Returns max 25 segments of data in one go
            try: data += self.s_queue.get(False)
            except Queue.Emtpy: break
            data_segments += 1
        
        return data


    def close(self):
        """Cleans up any internal state by at least destroying the instance of
        the lossy layer in use. Also called by the destructor of this socket.

        Do not confuse with shutdown, which disconnects the connection.
        close destroys *local* resources, and should only be called *after*
        shutdown.

        Probably does not need to be modified, but if you do, be careful to
        gate all calls to destroy resources with checks that destruction is
        valid at this point -- this method will also be called by the
        destructor itself. The easiest way of doing this is shown by the
        existing code:
            1. check whether the reference to the resource is not None.
                2. if so, destroy the resource.
            3. set the reference to None.
        """
        if self._lossy_layer is not None:
            self._lossy_layer.destroy()
        self._lossy_layer = None


    def __del__(self):
        """Destructor. Do not modify."""
        self.close()
