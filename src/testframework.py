import unittest
import filecmp
import threading
import time
import sys

"""This exposes a constant bytes object called TEST_BYTES_128MIB which, as the
name suggests, is 128 MiB in size. You can send it, receive it, and check it
for equality on the receiving end.

Pycharm may complain about an unresolved reference. This is a lie. It simply
cannot deal with a python source file this large so it cannot resolve the
reference. Python itself will run it fine, though.

You can also use the file large_input.py as-is for file transfer.
"""
from large_input import TEST_BYTES_128MIB


INPUTFILE  = "large_input.py"
OUTPUTFILE = "testframework-output.file"
TIMEOUT = 100
WINSIZE = 100
INTF = "lo"
NETEM_ADD     = "sudo tc qdisc add dev {} root netem".format(INTF)
NETEM_CHANGE  = "sudo tc qdisc change dev {} root netem {}".format(INTF, "{}")
NETEM_DEL     = "sudo tc qdisc del dev {} root netem".format(INTF)
NETEM_CORRUPT = "corrupt 1%"
NETEM_DUP     = "duplicate 10%"
NETEM_LOSS    = "loss 10% 25%"
NETEM_REORDER = "delay 20ms reorder 25% 50%"
NETEM_DELAY   = "delay " + str(TIMEOUT) + "ms 20ms"
NETEM_ALL     = "{} {} {} {}".format(NETEM_CORRUPT, NETEM_DUP, NETEM_LOSS, NETEM_REORDER)


def run_command_with_output(command, input=None, cwd=None, shell=True):
    """run command and retrieve output"""
    import subprocess
    try:
        process = subprocess.Popen(command, cwd=cwd, shell=shell, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    except Exception as e:
        print("problem running command : \n   ", str(command), "\n problem: ", str(e), file=sys.stderr)

    [stdoutdata, stderrdata] = process.communicate(input)  # no pipes set for stdin/stdout/stdout streams so does effectively only just wait for process ends  (same as process.wait()

    if process.returncode:
        print(stderrdata, file=sys.stderr)
        print("problem running command : \n   ", str(command), "\n return value: ", process.returncode, file=sys.stderr)

    return stdoutdata

def run_command(command,cwd=None, shell=True):
    """run command with no output piping"""
    import subprocess
    process = None
    try:
        process = subprocess.Popen(command, shell=shell, cwd=cwd)
        print(str(process), file=sys.stderr)
    except Exception as e:
        print("problem running command : \n   ", str(command), "\n problem: ", str(e), file=sys.stderr)

    process.communicate()  # wait for the process to end

    if process.returncode:
        print("problem running command : \n   ", str(command), "\n return value: ", process.returncode, file=sys.stderr)

        
class TestbTCPFramework(unittest.TestCase):
    """Test cases for bTCP"""
    
    def setUp(self):
        """Setup before each test

        This is an example test setup that uses the client and server process
        to test your application. Feel free to use a different test setup.
        """
        # default netem rule (does nothing)
        run_command(NETEM_ADD)
        
        # launch localhost server
        self._server_thread = threading.Thread(target=run_command_with_output,
                                               args=("python3 server_app.py -w {} -t {} -o {}".format(WINSIZE, TIMEOUT, OUTPUTFILE), ))
        self._server_thread.start()
        

    def tearDown(self):
        """Clean up after every test

        This is an example test setup that uses the client and server process
        to test your application. Feel free to use a different test setup.
        """
        # clean the environment
        run_command(NETEM_DEL)
        
        # close server
        # no actual work to do for this for our given implementation:
        # run_command_with_output terminates once the application it runs
        # terminates; so the thread should terminate by itself after the client
        # application disconnects from the server. All we do is a simple check
        # to see whether the server actually terminates.
        self._server_thread.join(timeout=10)
        if self._server_thread.is_alive():
            print("Something is keeping your server process alive. This may indicate a problem with shutting down.", file=sys.stderr)


    def test_ideal_network(self):
        """reliability over an ideal network

        This is an example testcase that uses the client and server process
        to test your application. Feel free to use a different test setup.
        """
        # setup environment (nothing to set)

        # launch localhost client connecting to server
        run_command_with_output("python3 client_app.py -w {} -t {} -i {}".format(WINSIZE, TIMEOUT, INPUTFILE))
        
        # client sends content to server
        
        # server receives content from client
        
        # content received by server matches the content sent by client
        assert filecmp.cmp(INPUTFILE, OUTPUTFILE)


    def test_flipping_network(self):
        """reliability over network with bit flips 
        (which sometimes results in lower layer packet loss)"""
        # setup environment
        run_command(NETEM_CHANGE.format(NETEM_CORRUPT))
        
        # launch localhost client connecting to server
        
        # client sends content to server
        
        # server receives content from client
        
        # content received by server matches the content sent by client


    def test_duplicates_network(self):
        """reliability over network with duplicate packets"""
        # setup environment
        run_command(NETEM_CHANGE.format(NETEM_DUP))
        
        # launch localhost client connecting to server
        
        # client sends content to server
        
        # server receives content from client
        
        # content received by server matches the content sent by client


    def test_lossy_network(self):
        """reliability over network with packet loss"""
        # setup environment
        run_command(NETEM_CHANGE.format(NETEM_LOSS))
        
        # launch localhost client connecting to server
        
        # client sends content to server
        
        # server receives content from client
        
        # content received by server matches the content sent by client


    def test_reordering_network(self):
        """reliability over network with packet reordering"""
        # setup environment
        run_command(NETEM_CHANGE.format(NETEM_REORDER))
        
        # launch localhost client connecting to server
        
        # client sends content to server
        
        # server receives content from client
        
        # content received by server matches the content sent by client


    def test_delayed_network(self):
        """reliability over network with delay relative to the timeout value"""
        # setup environment
        run_command(NETEM_CHANGE.format(NETEM_DELAY))
        
        # launch localhost client connecting to server
        
        # client sends content to server
        
        # server receives content from client
        
        # content received by server matches the content sent by client


    def test_allbad_network(self):
        """reliability over network with all of the above problems"""

        # setup environment
        run_command(NETEM_CHANGE.format(NETEM_ALL))
        
        # launch localhost client connecting to server
        
        # client sends content to server
        
        # server receives content from client
        
        # content received by server matches the content sent by client   

  
#    def test_command(self):
#        #command=['dir','.']
#        out = run_command_with_output("dir .")
#        print(out)
        

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="bTCP tests")
    parser.add_argument("-w", "--window",
                        help="Define bTCP window size used",
                        type=int, default=100)
    parser.add_argument("-t", "--timeout",
                        help="Define the timeout value used (ms)",
                        type=int, default=TIMEOUT)
    args, extra = parser.parse_known_args()
    TIMEOUT = args.timeout
    WINSIZE = args.window
    
    # Pass the extra arguments to unittest
    sys.argv[1:] = extra

    # Start test suite
    unittest.main()