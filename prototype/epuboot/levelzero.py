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

class LevelZeroFab(object):

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

class LevelZeroInstance(object):

    def __init__(self, instance, readpgm, sshusername, sshkey, log=logging):
        self.instance = instance
        self.stderr_str = ""
        self.stdout_str = ""
        self.stderr_eof = False
        self.stdout_eof = False
        self.p = None
        self.post_rc = None
        self.sshkey = sshkey
        self.sshusername = sshusername
        self.poll_hostcount = 0
        self.ready_p = None
        self.post_p = None
        self.ready_rc = None
        self.readpgm = readpgm
        self.fab_error_count = 0
        self.fab_error_max = 10
        self.log = log
        self._hostname = None

    def get_instance_id(self):
        return self.instance.id

    def get_stderr(self):
        s = self.stderr_str
        self.stderr_str = ""
        return s

    def get_stdout(self):
        s = self.stdout_str
        self.stdout_str = ""
        return s

    def get_post_rc(self):
        return self.post_rc

    def get_ready_rc(self):
        return self.ready_rc

    def poll(self, poll_period=1):
        """
        Poll the state of the instance.  Return None if the ready program
        has not yet completed, otherwise return the exit code of the ready
        program.
        """

        # if the ready program has been started either poll it or return
        # if it has finished
        if self.ready_p:
            if not self.ready_rc:
                rc = self._poll_process(self.ready_p, poll_period)
                if rc == 1:
                    # retry fab 
                    self.fab_error_count = self.fab_error_count + 1
                    if self.fab_error_count < self.fab_error_max:
                        self.ready_p = None
                else:
                    self.ready_rc = rc
            return self.ready_rc

        # if the ready program has not yet been finished, check the state
        # of the vm.  If it has just reached 'running' start the ready program
        rc = self._poll_host()
        # if the rc is true, start the ready program
        if rc:
            self.ready_p = self._run_fab(self.readpgm)
        return None

    def launch_post_program(self, post_pgm, poll_period=1):
        rc = poll()
        if rc == None:
            raise Exception("You cannot launch the post program until the ready program has completed")
        self.post_p = self._run_fab(post_pgm)

    def poll_post(self):
        """
        Poll the post program.
        """
        if not self.post_p:
            raise Exception("The post prgram has not yet been started")
        if not self.post_rc:
            self.post_rc = self._poll_process(self.post_p, poll_period)
        return self.post_rc

    def get_hostname(self):
        return self._hostname

    def _poll_host(self):
        # just to make sure we get some rest
        time.sleep(.1)
        try:
            if self.instance.state != "running":
                self.instance.update()
            if self.instance.state != "running":
                if self.instance.state != "pending":
                    raise Exception("The current state is %s.  Never reached state running" % (self.instance.state))
            else:
                self._hostname = self.instance.public_dns_name
                return True
        except EC2ResponseError, ecex:
            # We allow this error to occur once.  It takes ec2 some time 
            # to be sure of the instance id
            if self.poll_hostcount > 0:
                # if we poll too quick sometimes aws cannot find the id
                self.log.error(ecex)
                raise ecex
            self.poll_hostcount = self.poll_hostcount + 1
        return False

    def _poll_process(self, p, poll_period=1):
        eof = self._read_output(p, poll_period)
        if not eof:
            return None
        rc = p.poll()
        return rc

    def _read_output(self, p, poll_period):
        selectors = []
        if not self.stdout_eof:
            selectors.append(p.stdout)
        if not self.stderr_eof:
            selectors.append(p.stderr)

        (rlist,wlist,elist) = select.select(selectors, [], [], poll_period)
        for f in rlist:
            line = f.readline()
            if f == p.stdout:
                # we assume there will be a full line or eof
                # not the fastest str concat, but this is small
                self.stdout_str = self.stdout_str + line
                if line == "":
                    self.stdout_eof = True
            else:            
                self.stderr_str = self.stderr_str + line
                if line == "":
                    self.stderr_eof = True

        return self.stderr_eof and self.stdout_eof

    def _run_fab(self, readypgm):
        # run fab
        cmd = "fab -D"
        if self.sshusername:
            cmd = "%s -u %s" % (cmd, self.sshusername)
        if self.sshkey:
            cmd = "%s -i %s" %(cmd, self.sshkey)
        cmd = "%s -f levelzero setup_and_test_vm:hosts=%s,testpgm=%s,args=#HELLO" % (cmd, self.instance.public_dns_name, readypgm)

        self.log.debug(cmd)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        return p

class LevelZeroLaunch(object):

    def __init__(self, log=None, iaaskeyname="ooi", iaashostname=None, iaasport=None, sshusername="ubuntu",  sshkey=None):

        if sshkey == None:
            sshkey=os.path.expanduser("~/.ssh/ooi.pem")
        if log == None:
            log = logging

        self.log = log
        self.iaaskeyname = iaaskeyname
        self.iaashostname = iaashostname
        self.iaasport = iaasport
        self.sshusername = sshusername
        self.sshkey = sshkey

        # todo, trap exception and throw nicer error
        self.nimbus_key = os.environ.get('NIMBUS_KEY')
        self.nimbus_secret = os.environ.get('NIMBUS_SECRET')

        self.ec2_key = os.environ.get('AWS_ACCESS_KEY_ID')
        self.ec2_secret = os.environ.get('AWS_SECRET_ACCESS_KEY')

    def launch(self, baseimage, readypgm, instancetype="t1.micro"):
        con = self._get_connection()
        reservation = con.run_instances(baseimage,
                                        instance_type=instancetype,
                                        key_name=self.iaaskeyname)
        return LevelZeroInstance(reservation.instances[0], readypgm, self.sshusername, self.sshkey)

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
                    self.log.info(s)
                s = i.get_stdout()
                if s != "":
                    s = "[%s:stdout] %s" % (i.get_hostname(), s)
                    self.log.info(s)
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
        if not self.iaashostname:
            con = EC2Connection(self.ec2_key, self.ec2_secret)
        else:
            region = RegionInfo(name="nimbus", endpoint=self.iaashostname)
            if not self.iaasport:
                con =  boto.connect_ec2(self.nimbus_key, self.nimbus_secret,
                                        region=region)
            else:
                con =  boto.connect_ec2(self.nimbus_key, self.nimbus_secret,
                                        port=self.iaasport, region=region)
        return con


# this is what fab actually calls
def setup_and_test_vm(testpgm, args=None):
    lz = LevelZeroFab(testpgm, args=args)
    lz.setup_vm()
    lz.run_ready()


def main(argv=sys.argv[1:]):
    lzl = LevelZeroLaunch()

    if len(argv) > 1:
        count = int(argv[1])
    else:
        count = 1

    inst_list = []
    for i in range(0, count):
        pz = lzl.launch('ami-30f70059', argv[0])
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

