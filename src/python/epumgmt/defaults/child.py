from datetime import datetime
import os
import signal
import subprocess
import sys
import time

try:
    from threading import Thread
except ImportError:
    from dummy_threading import Thread

def child(cmd, timeout=0.0):
    """Run a system program.
    
    Required parameter:
    
    * cmd -- command to run, string
    
    Keyword parameter:
    
    * timeout -- how many seconds to wait before SIGKILL (int or float)
    Default is 0 seconds which means no killing.
    
    Return (was_killed, exitcode, stdout, stderr)
    
    * was_killed -- boolean, true if it timed out and was killed
    
    * exitcode -- integer exit code, only relevant if killed is False
    See:
    http://docs.python.org/library/subprocess.html#subprocess.Popen.returncode
    
    * stdout -- stdout or None
    
    * stderr -- stderr or None
    
    """
    
    thr = RunThread(cmd)
    
    if timeout <= 0:
        thr.start()
        thr.join()
        
        # That is it.
        return (False, thr.exit, thr.stdout, thr.stderr)
        
    # Timeout is requested
    
    start = datetime.now()
    thr.start()
    
    killed = False
    while True:
        thr.join(0.1)
        if not thr.isAlive():
            break
        
        elapsed = (datetime.now() - start)
        if elapsed.seconds > timeout:
            try:
                pid = thr.pid
                if pid < 1:
                    sys.stderr.write("Time elapsed but no PID to kill!\n")
                    break
                os.kill(thr.pid, signal.SIGKILL)
                os.waitpid(-1, os.WNOHANG)
            except OSError,e:
                pass #sys.stderr.write("%s\n" % e)
            killed = True
            break
    
    return (killed, thr.exit, thr.stdout, thr.stderr)


# -------------------------------------------------------------------------

    
class RunThread(Thread):
    
    def __init__ (self, cmd):
        """Populate the thread.
        
        Required parameters:
        
        * cmd -- command to run
        
        Properties available:
        
        * pid -- pid of the child, or -1
        
        * stdout -- stdout data or None
        
        * stderr -- stderr data or None
        
        * retcode -- exit of child process: 0, positive exit code, negative
        exit means signal. See:
        http://docs.python.org/library/subprocess.html#subprocess.Popen.returncode
        """
        
        Thread.__init__(self)
        self.cmd = cmd
        self.exit = None
        self.stdout = None
        self.stderr = None
        self.pid = -1
        
    def run(self):
        process = subprocess.Popen(self.cmd, shell=True, 
                                   executable="/bin/bash",
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        self.pid = process.pid
        (self.stdout, self.stderr) = process.communicate()
        self.exit = process.returncode
