"""
Students should NOT need to modify any code in this file!

However, do read the docstrings to understand what's going on.
"""


import socket
import select
import sys
import threading
from btcp.constants import *


def handle_incoming_segments(btcp_socket, event, udp_socket):
    """This is the main method of the "network thread".

    Continuously read from the socket and whenever a segment arrives,
    call the lossy_layer_segment_received method of the associated socket.

    If no segment is received for TIMER_TICK ms, call the lossy_layer_tick
    method of the associated socket.

    When flagged, return from the function. This is used by LossyLayer's
    destructor. Note that destruction will *not* attempt to receive or send any
    more data; after event gets set the method will send one final segment to
    the transport layer, or give one final tick if no segment is received in
    TIMER_TICK ms, then return.

    Students should NOT need to modify any code in this method.
    """
    while not event.is_set():
        # We do not block here, because we might never check the loop condition in that case
        rlist, wlist, elist = select.select([udp_socket], [], [], TIMER_TICK / 1000)
        if rlist:
            segment, address = udp_socket.recvfrom(SEGMENT_SIZE)
            btcp_socket.lossy_layer_segment_received(segment)
            # We *assume* here that students aren't leaving multiple processes
            # sending segments from different remote IPs and ports running.
            # We *could* check the address for validity but then we'd have
            # to resolve hostnames etc and honestly I don't see a pressing need
            # for that.
        else:
            btcp_socket.lossy_layer_tick()


class LossyLayer:
    """The lossy layer emulates the network layer in that it provides bTCP with
    an unreliable segment delivery service between a and b.

    When the lossy layer is created, a thread (the "network thread") is started
    that calls handle_incoming_segments. When the lossy layer is destroyed, it
    will signal that thread to end, join it, wait for it to terminate, then
    destroy its UDP socketet.

    Students should NOT need to modify any code in this class.
    """
    def __init__(self, btcp_socket, local_ip, local_port, remote_ip, remote_port):
        self._bTCP_socket = btcp_socket
        self._remote_ip = remote_ip
        self._remote_port = remote_port
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._udp_socket.bind((local_ip, local_port))
        self._event = threading.Event()
        self._thread = threading.Thread(target=handle_incoming_segments,
                                        args=(self._bTCP_socket, self._event, self._udp_socket))
        self._thread.start()


    def __del__(self):
        self.destroy()


    def destroy(self):
        """Flag the thread that it can stop, wait for it to do so, then close
        the lossy segment delivery service's UDP socket.

        Should be safe to call multiple times, so safe to call from __del__.
        """
        if self._event is not None and self._thread is not None:
            self._event.set()
            self._thread.join()
        if self._udp_socket is not None:
            self._udp_socket.close()
        self._event = None
        self._thread = None
        self._udp_socket = None


    def send_segment(self, segment):
        """Put the segment into the network

        Should be safe to call from either the application thread or the
        network thread.
        """
        bytes_sent = self._udp_socket.sendto(segment, (self._remote_ip, self._remote_port))
        if bytes_sent != len(segment):
            print("The lossy layer was only able to send {} bytes of that segment!".format(bytes_sent), file=sys.stderr)
