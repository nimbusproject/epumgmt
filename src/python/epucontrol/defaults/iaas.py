import os
import subprocess
import time

from boto.ec2.connection import EC2Connection
from epucontrol.api.exceptions import *
import epucontrol.main.ec_args as ec_args
from epucontrol.main import ACTIONS

class DefaultIaaS:
    
    """Launch/contextualize VM instances
    
    Uses boto+fabfile.  Will be implemented via Nimboss in the future,
    this is more flexible for heavy development.  Note that any VMs that
    EPU software launches as compensation will only use Nimboss and the
    context broker, there is no fab involved there.
    """
    
    def __init__(self, params, common):
        self.p = params
        self.c = common
        self.validated = False
        self.grace = 0
        self.graceleft = 0
        
        self.baseimage = None
        self.ec2_key = None
        self.ec2_secret = None
        self.instancetype = None
        self.sshkeyname = None
        self.username = None
        self.localsshkeypath = None
        
    def validate(self):
        
        action = self.p.get_arg_or_none(ec_args.ACTION)
        if action not in [ACTIONS.CREATE]:
            if self.c.trace:
                self.c.log.debug("validation for IaaS module complete, not a relevant action")
            return
        
        
        # In the near future, this will branch on IaaS, e.g. EC2 vs. Nimbus.
        # And use Nimboss to do contextualization.  Currently, instead this
        # is using boto + fabfile.  At that future point, this will need to
        # validate hostnames, availability zones, context broker address, etc.
    
        self.ec2_key = os.environ.get('AWS_ACCESS_KEY_ID')
        self.ec2_secret = os.environ.get('AWS_SECRET_ACCESS_KEY')
        if not self.ec2_key or not self.ec2_secret:
            raise InvalidConfig("You need to export both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to the environment.")
        
        graceperiod = self.p.get_arg_or_none(ec_args.GRACEPERIOD)
        if graceperiod:
            self.grace = int(graceperiod)
            self.graceleft = self.grace
        
        confsection = self.p.get_conf_or_none("iaas", "confsection")
        argsection = self.p.get_arg_or_none(ec_args.IAASCONF)
        section = None
        if argsection:
            section = argsection
        elif confsection:
            section = confsection
        else:
            raise InvalidConfig("Missing the iaas:confsection configuration")
            
        self.baseimage = self.p.get_conf_or_none(section, "baseimage")
        if not self.baseimage:
            raise InvalidConfig("Missing the baseimage configuration")
            
        self.sshkeyname = self.p.get_conf_or_none(section, "sshkeyname")
        if not self.sshkeyname:
            raise InvalidConfig("Missing the sshkeyname configuration")
        
        self.instancetype = self.p.get_conf_or_none(section, "instancetype")
        if not self.instancetype:
            raise InvalidConfig("Missing the instancetype configuration")
            
        self.username = self.p.get_conf_or_none(section, "username")
        if not self.username:
            raise InvalidConfig("Missing the username configuration")
            
        self.localsshkeypath = self.p.get_conf_or_none(section, "localsshkeypath")
        if not self.localsshkeypath:
            raise InvalidConfig("Missing the localsshkeypath configuration")
        if not os.path.exists(self.localsshkeypath):
            self.localsshkeypath = os.path.expanduser(self.localsshkeypath)
            if not os.path.exists(self.localsshkeypath):
                raise InvalidConfig("localsshkeypath is not a valid file: %s" % self.localsshkeypath)
            
        
        self.validated = True
        self.c.log.debug("baseimage: " + self.baseimage)
        self.c.log.debug("ec2_key: " + self.ec2_key)
        self.c.log.debug("ec2_secret: [REDACTED]")
        self.c.log.debug("instancetype: " + self.instancetype)
        self.c.log.debug("sshkeyname: " + self.sshkeyname)
        self.c.log.debug("username: " + self.username)
        self.c.log.debug("localsshkeypath: " + self.localsshkeypath)
        self.c.log.debug("validated IaaS module")

    def launch(self):
        """Return (instanceid, hostname) tuple or Exception""" 
            
        if not self.validated:
            raise ProgrammingError("operation called without necessary validation")
            
        # In the future, these things will be compromised of one Nimboss call
        (instanceid, hostname) = self._launch_ec2()
        
        # Firewall not letting pings through at moment, revisit
        #self._wait_for_ping(hostname)
        self._wait_for_access(hostname)
        
        return (instanceid, hostname)
        
    def _launch_ec2(self):
        
        con = EC2Connection(self.ec2_key, self.ec2_secret)
        
        self.c.log.info("Launching baseimage '%s' with instance type '%s' and key name '%s'" % (self.baseimage, self.instancetype, self.sshkeyname))
        
        reservation = con.run_instances(self.baseimage,
                                        instance_type=self.instancetype,
                                        key_name=self.sshkeyname)

        instance = reservation.instances[0]
        self.c.log.info("Instance launched: %s" % instance.id)
        time.sleep(10)
        
        while True:
            self.c.log.debug("Checking instance state: %s" % instance.id)
            if instance.update() == 'running':
                break
            time.sleep(4)
            if self.grace > 0:
                self.graceleft -= 4
                if self.c.trace:
                    self.c.log.debug("grace period left: %d" % self.graceleft)
                
                if self.graceleft < 0:
                    msg = "Instance %s did not reach 'running' in time (%d secs elapsed)" % (instance.id, elapsed_secs)
                    self.c.log.error(msg)
                    try:
                        self.c.log.error("Destroying instance %s" % instance.id)
                        instance.stop()
                    except Exception,e:
                        msg2 = "Problem destroying instance: %s" % e
                        self.c.log.error(msg2)
                        raise UnexpectedError(msg + ": " + msg2)
                    raise UnexpectedError(msg + ".  Destroyed.")
        
        self.c.log.info("Instance running: %s | Hostname: %s" % (instance.id, instance.public_dns_name))
        
        sshcmd = self.ssh_cmd(instance.public_dns_name)
        self.c.log.info("SSH suggestion: %s" % ' '.join(sshcmd))
        
        return (instance.id, instance.public_dns_name)
       
    def _wait_for_ping(self, hostname):
        """Wait for ping to succeed.  'Running' does not mean we can log in
        and do anything yet.  Fab does not seem to hang out correctly
        otherwise."""
        
        while True:
            # Wait for one ping to succeed; bail after 5 seconds
            args = ["ping", "-c", "1", "-w", "5", hostname]
            if self._one_cmd(args):
                break
            time.sleep(0.5)

    def _wait_for_access(self, hostname):
        """Wait for ssh /bin/true to succeed.  'Running' does not mean
        we can log in and do anything yet.  Fab does not seem to hang out
        correctly otherwise."""
        
        # give it at least a little time to boot, logs are filling with errors
        time.sleep(3.0)
        
        while True:
            args = self.ssh_cmd(hostname)
            args.append("/bin/true")
            if self._one_cmd(args):
                break
            time.sleep(0.5)
        
    def ssh_cmd(self, hostname):
        return ["ssh", "-oStrictHostKeyChecking=no", "-i", self.localsshkeypath, "-l", self.username, hostname]
        
    def _one_cmd(self, args):
        """See _wait_for_access() and _wait_for_ping()"""
        
        cmd = ' '.join(args)
        self.c.log.debug("command = '%s'" % cmd)
        try:
            proc = subprocess.Popen(args, 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE)
            (output,error) = proc.communicate()
            ret = proc.wait()
            while ret == None:
                self.c.log.debug("wait returned, but child has not exited yet?")
                time.sleep(0.2)
                ret = proc.wait()
            
            if ret == 0:
                self.c.log.debug("command succeeded: '%s'" % cmd)
                return True
            else:
                errmsg = "problem running command, "
                if ret < 0:
                    errmsg += "killed by signal:"
                if ret > 0:
                    errmsg += "exited non-zero:"
                errmsg += "'%s' ::: return code" % cmd
                errmsg += ": %d ::: error:\n%s\noutput:\n%s" % (ret, error, output)
                
                # these commands will commonly fail 
                if self.c.trace:
                    self.c.log.debug(errmsg)
                return False
        except:
            self.c.log.exception("Severe problem running '%s'" % cmd)
            # This is not normal, bail out.
            raise

    def contextualize_base_image(self, services, hostname):
        
        if not services:
            raise ProgrammingError("operation called without services module")
        
        if not self.validated or not services.validated:
            raise ProgrammingError("operation called without necessary validation")
        
        self.c.log.info("Calling fabric contextualization for service %s on host %s" % (services.servicename, hostname))
        
        # A special case, provisioner needs a secrets transfer
        fabtask = "bootstrap"
        if services.servicename == "provisioner":
            fabtask = "bootstrap_cei"
        
        rolesfile = services.chefrolespath
        
        self.c.log.debug("fabtask: '%s'" % fabtask)
        
        args = [services.fablaunch, fabtask, self.username, self.localsshkeypath, hostname, rolesfile]
        
        cmd = ' '.join(args)
        self.c.log.debug("command = '%s'" % cmd)
        
        proc = subprocess.Popen(args, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
        (output,error) = proc.communicate()
        ret = proc.wait()
        while ret == None:
            self.c.log.debug("wait returned, but child has not exited yet?")
            ret = proc.wait()
            
        if ret != 0:
            errmsg = "problem running command, "
            if ret < 0:
                errmsg += "killed by signal:"
            if ret > 0:
                errmsg += "exited non-zero:"
            errmsg += "'%s' ::: return code" % cmd
            errmsg += ": %d ::: error:\n%s\noutput:\n%s" % (ret, error, output)
            raise UnexpectedError(errmsg)
        
    def terminate_ids(self, instanceids):
        con = EC2Connection(self.ec2_key, self.ec2_secret)
        con.terminate_instances(instanceids)
        