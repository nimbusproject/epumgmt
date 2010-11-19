import sys
import subprocess
import time
import os
from fabric.api import run, sudo, put
import logging
import boto
from boto.ec2.connection import EC2Connection
from boto.ec2.regioninfo import RegionInfo
from boto.exception import EC2ResponseError
import select

class BootLevelFab(object):

    def __init__(self, readyprogram, remoteready='/tmp/nimbus-remoteready', args=None):
        self.readyprogram = readyprogram
        self.remoteready = remoteready
        if args == None:
            self.pgm_args = []
        else:
            delim = args[0]
            self.pgm_args = args[1:].split(delim)

    def setup_vm(self):
        put(self.readyprogram, self.remoteready)

    def run_ready(self):
        cmd = self.remoteready
        for a in self.pgm_args:
            cmd = cmd + " " + a
        res = sudo(cmd)
        print res
        print "READYCODE: %d" % (res.failed)

class BootLevelReady(object):

    def __init__(self, sshusername, sshkey, readypgm=None, instance=None, vmhostname=None, log=logging):

        if not instance and not vmhostname:
            raise Exception("You must specify either an image to run, or a running image hostname")
        if instance and vmhostname:
            raise Exception("You cannot specify an instance AND a vmhostname")
        self._instance = instance
        self._vmhostname = vmhostname
        self._stderr_str = ""
        self._stdout_str = ""
        self._stderr_eof = False
        self._stdout_eof = False
        self._sshkey = sshkey
        self._sshusername = sshusername
        self._poll_hostcount = 0
        self._ready_p = None
        self._ready_rc = None
        self._readypgm = readypgm
        self._fab_error_count = 0
        self._fab_error_max = 10
        self._log = log

    def get_instance_id(self):
        if self._instance == None:
            return None
        return self._instance.id

    def get_stderr(self):
        s = self._stderr_str
        self._stderr_str = ""
        return s

    def get_stdout(self):
        s = self._stdout_str
        self._stdout_str = ""
        return s

    def get_ready_rc(self):
        return self._ready_rc

    def poll(self, poll_period=1):
        """
        Poll the state of the instance.  Return None if the ready program
        has not yet completed, otherwise return the exit code of the ready
        program.
        """

        # if the ready program has been started either poll it or return
        # if it has finished
        if self._ready_p:
            if not self._ready_rc:
                rc = self._poll_process(self._ready_p, poll_period)
                if rc == 1:
                    # retry fab 
                    self._fab_error_count = self._fab_error_count + 1
                    if self._fab_error_count < self._fab_error_max:
                        self._ready_p = None
                else:
                    self._ready_rc = rc
            return self._ready_rc

        # if the ready program has not yet been finished, check the state
        # of the vm.  If it has just reached 'running' start the ready program
        rc = self._poll_host()
        # if the rc is true, start the ready program
        if rc:
            self._ready_p = self._run_fab(self._readypgm)
        return None

    def get_hostname(self):
        return self._vmhostname

    def _poll_host(self):
        # if this was lauched with an existing ip, then this is done
        if self._vmhostname:
            return True

        # just to make sure we get some rest, the user may likely call
        # poll in a tight loop
        time.sleep(.1)
        try:
            if self._instance.state != "running":
                self._instance.update()
            if self._instance.state != "running":
                if self._instance.state != "pending":
                    raise Exception("The current state is %s.  Never reached state running" % (self._instance.state))
            else:
                self._hostname = self._instance.public_dns_name
                return True
        except EC2ResponseError, ecex:
            # We allow this error to occur once.  It takes ec2 some time 
            # to be sure of the instance id
            if self._poll_hostcount > 0:
                # if we poll too quick sometimes aws cannot find the id
                self._log.error(ecex)
                raise ecex
            self._poll_hostcount = self._poll_hostcount + 1
        return False

    def _poll_process(self, p, poll_period=1):
        eof = self._read_output(p, poll_period)
        if not eof:
            return None
        rc = p.poll()
        return rc

    def _read_output(self, p, poll_period):
        selectors = []
        if not self._stdout_eof:
            selectors.append(p.stdout)
        if not self._stderr_eof:
            selectors.append(p.stderr)

        (rlist,wlist,elist) = select.select(selectors, [], [], poll_period)
        for f in rlist:
            line = f.readline()
            if f == p.stdout:
                # we assume there will be a full line or eof
                # not the fastest str concat, but this is small
                self._stdout_str = self._stdout_str + line
                if line == "":
                    self._stdout_eof = True
            else:            
                self._stderr_str = self._stderr_str + line
                if line == "":
                    self._stderr_eof = True

        return self._stderr_eof and self._stdout_eof

    def _run_fab(self, readypgm):
        # run fab
        cmd = "fab -D"
        if self._sshusername:
            cmd = "%s -u %s" % (cmd, self._sshusername)
        if self._sshkey:
            cmd = "%s -i %s" %(cmd, self._sshkey)
        cmd = "%s -f bootlevel setup_and_test_vm:hosts=%s,testpgm=%s,args=#HELLO" % (cmd, self._instance.public_dns_name, readypgm)

        self._log.debug(cmd)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        return p

class BootLevelLaunch(object):

    def __init__(self, log=logging, iaaskeyname="ooi", iaashostname=None, iaasport=None, sshusername="ubuntu",  sshkey=os.path.expanduser("~/.ssh/ooi.pem")):

        self._log = log
        self._iaaskeyname = iaaskeyname
        self._iaashostname = iaashostname
        self._iaasport = iaasport
        self._sshusername = sshusername
        self._sshkey = sshkey

        # todo, trap exception and throw nicer error
        self._nimbus_key = os.environ.get('NIMBUS_KEY')
        self._nimbus_secret = os.environ.get('NIMBUS_SECRET')

        self._ec2_key = os.environ.get('AWS_ACCESS_KEY_ID')
        self._ec2_secret = os.environ.get('AWS_SECRET_ACCESS_KEY')

    def launch(self, readypgm=None, baseimage=None, hostname=None, instancetype="t1.micro"):
        con = self._get_connection()
        instance = None
        if baseimage != None:
            reservation = con.run_instances(baseimage,
                                        instance_type=instancetype,
                                        key_name=self._iaaskeyname)
            instance = reservation.instances[0]
        return BootLevelReady(self._sshusername, self._sshkey, readypgm=readypgm, instance=instance, vmhostname=hostname)

    def barrier(self, instance_list, poll_period=10, max_polls=1024):
        """
        This program accepts a list of instances and blocks until all of 
        ready programs have completed.  The tupple (success, [rc list]) is
        returned.  success is a boolean that is true if all instance ready 
        programs reported success and false if any one (or more) failed.
        The rc_list gives the specfic rc or each instance in the order it
        was given to the call
        """
        it_count = 0
        while it_count < max_polls:
            # would be more efficient to remove instance then to keep polling
            rc_list = []
            done = True
            success = True
            for i in instance_list:
                rc = i.poll(poll_period)
                rc_list.append(rc)
                if rc == None:
                    done = False
                if rc != 0:
                    success = False

                s = i.get_stderr()
                if s != "":
                    s = "[%s:stderr] %s" % (i.get_hostname(), s)
                    self._log.info(s)
                s = i.get_stdout()
                if s != "":
                    s = "[%s:stdout] %s" % (i.get_hostname(), s)
                    self._log.info(s)
            if done:
                return (success, rc_list)
            it_count = it_count + 1

        # if we get this far the iteration count expired
        raise Exception("Iteration count %d exceeded %d"%(it_count,max_polls))
   
    def terminate(self, instance_list):
        con = self._get_connection()
        instanceids = [i.get_instance_id() for i in instance_list]
        return con.terminate_instances(instanceids)

    def _get_connection(self):
        # see comments in validate()
        if not self._iaashostname:
            con = EC2Connection(self._ec2_key, self._ec2_secret)
        else:
            region = RegionInfo(name="nimbus", endpoint=self._iaashostname)
            if not self._iaasport:
                con =  boto.connect_ec2(self._nimbus_key, self._nimbus_secret,
                                        region=region)
            else:
                con =  boto.connect_ec2(self._nimbus_key, self._nimbus_secret,
                                        port=self._iaasport, region=region)
        return con


# this is what fab actually calls
def setup_and_test_vm(testpgm, args=None):
    lz = BootLevelFab(testpgm, args=args)
    lz.setup_vm()
    lz.run_ready()

def make_logger():
    logger = logging.getLogger('debug_logger')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger



def main(argv=sys.argv[1:]):
    lzl = BootLevelLaunch(log=make_logger())

    if len(argv) > 1:
        count = int(argv[1])
    else:
        count = 1

    inst_list = []
    for i in range(0, count):
        pz = lzl.launch(readypgm=argv[0], baseimage='ami-30f70059')
        inst_list.append(pz)

    (success, rc_list) = lzl.barrier(inst_list)
    print "success = %s" % (str(success))
    for rc in rc_list:
        print rc

    lzl.terminate(inst_list)
    if success:
        return 0
    else:
        return 1


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)

