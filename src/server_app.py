#!/usr/bin/env python3

import argparse
from btcp.server_socket import BTCPServerSocket

"""This exposes a constant bytes object called TEST_BYTES_128MIB which, as the
name suggests, is 128 MiB in size. You can send it, receive it, and check it
for equality on the receiving end.

Pycharm may complain about an unresolved reference. This is a lie. It simply
cannot deal with a python source file this large so it cannot resolve the
reference. Python itself will run it fine, though.

You can also use the file large_input.py as-is for file transfer.
"""
from large_input import TEST_BYTES_128MIB


def btcp_file_transfer_server():
    """This method should implement your bTCP file transfer server. We have
    provided a bare bones command line argument parser and create the server
    socket. The rest is up to you -- feel free to use helper methods.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--window",
                        help="Define bTCP window size",
                        type=int, default=100)
    parser.add_argument("-t", "--timeout",
                        help="Define bTCP timeout in milliseconds",
                        type=int, default=100)
    parser.add_argument("-o", "--output",
                        help="Where to store the file",
                        default="output.file")
    args = parser.parse_args()

    # Create a bTCP server socket
    s = BTCPServerSocket(args.window, args.timeout)
    # TODO Write your file transfer server code here using your
    # BTCPServerSocket's accept, and recv methods.

    # Clean up any state
    s.close()


if __name__ == "__main__":
    btcp_file_transfer_server()
