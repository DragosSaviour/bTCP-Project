#!/usr/bin/env python3

import argparse
from btcp.client_socket import BTCPClientSocket

"""This exposes a constant bytes object called TEST_BYTES_128MIB which, as the
name suggests, is 128 MiB in size. You can send it, receive it, and check it
for equality on the receiving end.

Pycharm may complain about an unresolved reference. This is a lie. It simply
cannot deal with a python source file this large so it cannot resolve the
reference. Python itself will run it fine, though.

You can also use the file large_input.py as-is for file transfer.
"""
from large_input import TEST_BYTES_128MIB


def btcp_file_transfer_client():
    """This method should implement your bTCP file transfer client. We have
    provided a bare bones command line argument parser and create the client
    socket. The rest is up to you -- feel free to use helper methods.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--window",
                        help="Define bTCP window size",
                        type=int, default=100)
    parser.add_argument("-t", "--timeout",
                        help="Define bTCP timeout in milliseconds",
                        type=int, default=100)
    parser.add_argument("-i", "--input",
                        help="File to send",
                        default="large_input.py")
    args = parser.parse_args()

    # Create a bTCP client socket with the given window size and timeout value
    s = BTCPClientSocket(args.window, args.timeout)
    # TODO Write your file transfer client code using your implementation of
    # BTCPClientSocket's connect, send, and disconnect methods.

    # Clean up any state
    s.close()


if __name__ == "__main__":
    btcp_file_transfer_client()