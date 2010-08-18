import os
import time

import boto
from boto.ec2.connection import EC2Connection
from boto.ec2.regioninfo import RegionInfo
from epucontrol.api.exceptions import *
import epucontrol.main.ec_args as ec_args
from epucontrol.main import ACTIONS

import child

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
        self.nimbus_key = None
        self.nimbus_secret = None
        self.ec2_key = None
        self.ec2_secret = None
        self.instancetype = None
        self.sshkeyname = None
        self.ssh_username = None
        self.scp_username = None
        self.localsshkeypath = None
        self.custom_hostname = None
        self.custom_port = 0
        
    def validate(self):
        
        action = self.p.get_arg_or_none(ec_args.ACTION)
        if action not in [ACTIONS.CREATE, ACTIONS.LOGFETCH, ACTIONS.FETCH_KILL,
                          ACTIONS.FIND_WORKERS, ACTIONS.FIND_WORKERS_ONCE, ACTIONS.KILLRUN]:
            if self.c.trace:
                self.c.log.debug("validation for IaaS module complete, '%s' is not a relevant action" % action)
            return
        
        
        # In the near future, this will branch on generic IaaS and use Nimboss
        # to do contextualization.  Currently, instead this is using boto +
        # fabfile.  At that future point, this will need to validate hostnames,
        # availability zones, context broker address, etc.
        
        self.nimbus_key = os.environ.get('NIMBUS_KEY')
        self.nimbus_secret = os.environ.get('NIMBUS_SECRET')
    
        self.ec2_key = os.environ.get('AWS_ACCESS_KEY_ID')
        self.ec2_secret = os.environ.get('AWS_SECRET_ACCESS_KEY')
        
        graceperiod = self.p.get_arg_or_none(ec_args.GRACE_PERIOD)
        if graceperiod:
            self.grace = int(graceperiod)
            self.graceleft = self.grace
        
        confsection = self.p.get_conf_or_none("iaas", "confsection")
        argsection = self.p.get_arg_or_none(ec_args.IAAS_CONF)
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
            
        self.ssh_username = self.p.get_conf_or_none(section, "ssh_username")
        if not self.ssh_username:
            raise InvalidConfig("Missing the ssh_username configuration")
        
        self.scp_username = self.p.get_conf_or_none(section, "scp_username")
        if not self.scp_username:
            raise InvalidConfig("Missing the scp_username configuration")
            
        self.localsshkeypath = self.p.get_conf_or_none(section, "localsshkeypath")
        if not self.localsshkeypath:
            raise InvalidConfig("Missing the localsshkeypath configuration")
        if not os.path.exists(self.localsshkeypath):
            self.localsshkeypath = os.path.expanduser(self.localsshkeypath)
            if not os.path.exists(self.localsshkeypath):
                raise InvalidConfig("localsshkeypath is not a valid file: %s" % self.localsshkeypath)
            
        self.custom_hostname = self.p.get_conf_or_none(section, "custom_hostname")
        if not self.custom_hostname:
            self.c.log.debug("no custom endpoint for iaas (ignoring port)")
        else:
            self.c.log.debug("custom hostname: %s" % self.custom_hostname)
            self.custom_port = self.p.get_conf_or_none(section, "custom_port")
            if self.custom_port:
                self.custom_port = int(self.custom_port)
                if self.custom_port < 1:
                    raise InvalidConfig("custom_port looks invalid, %d less than 1?  Comment it out if it is unused." % self.custom_port)
                self.c.log.debug("custom port: %d" % self.custom_port)
                
        if self.custom_hostname:
            self.c.log.info("custom endpoint for iaas, looking for NIMBUS_KEY/NIMBUS_SECRET")
            if not self.nimbus_key or not self.nimbus_secret:
                raise InvalidConfig("You need to export both NIMBUS_KEY and NIMBUS_SECRET to the environment.")
        elif not self.ec2_key or not self.ec2_secret:
            raise InvalidConfig("You need to export both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to the environment.")
        
        self.validated = True
        self.c.log.debug("baseimage: " + self.baseimage)
        self.c.log.debug("ec2_key: " + self.ec2_key)
        self.c.log.debug("ec2_secret: [REDACTED]")
        self.c.log.debug("nimbus_key: " + self.nimbus_key)
        self.c.log.debug("nimbus_secret: [REDACTED]")
        self.c.log.debug("instancetype: " + self.instancetype)
        self.c.log.debug("sshkeyname: " + self.sshkeyname)
        self.c.log.debug("ssh_username: " + self.ssh_username)
        self.c.log.debug("scp_username: " + self.scp_username)
        self.c.log.debug("localsshkeypath: " + self.localsshkeypath)
        self.c.log.debug("validated IaaS module")

    def launch(self):
        """Return (instanceid, hostname) tuple or Exception""" 
            
        if not self.validated:
            raise ProgrammingError("operation called without necessary validation")
            
        # In the future, these things will be compromised of one Nimboss call
        (instanceid, hostname) = self._launch_iaas()
        
        # Firewall not letting pings through at moment, revisit
        #self._wait_for_ping(hostname)
        self._wait_for_access(hostname)
        
        return (instanceid, hostname)
        
    def _launch_iaas(self):
        
        con = self._get_connection()
        
        self.c.log.info("Launching baseimage '%s' with instance type '%s' and key name '%s'" % (self.baseimage, self.instancetype, self.sshkeyname))
        
        reservation = con.run_instances(self.baseimage,
                                        instance_type=self.instancetype,
                                        key_name=self.sshkeyname)

        instance = reservation.instances[0]
        self.c.log.info("Instance launched: %s" % instance.id)
        
        while True:
            time.sleep(7)
            self.c.log.debug("Checking instance state: %s" % instance.id)
            if instance.update() == 'running':
                break
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
        
        return (instance.id, instance.public_dns_name)
       
    def _wait_for_ping(self, hostname):
        """Wait for ping to succeed.  'Running' does not mean we can log in
        and do anything yet.  Fab does not seem to hang out correctly
        otherwise."""
        
        while True:
            # Wait for one ping to succeed; bail after 5 seconds
            args = ["ping", "-c", "1", "-w", "5", hostname]
            if self._run_one_cmd(args):
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
            cmd = ' '.join(args)
            self.c.log.debug("command = '%s'" % cmd)
            if self._run_one_cmd(args):
                break
            time.sleep(2.0)
        
    def ssh_cmd(self, hostname):
        """Return list of args for an SSH login"""
        return ["ssh", "-oStrictHostKeyChecking=no", "-i", self.localsshkeypath, "-l", self.ssh_username, hostname]
        
    def scp_cmd(self, hostname):
        """Return beginning of a list of args for a recursive (-r) SCP transfer.
        The 'user@host:' source bit is last.
        See "events.conf" for limiting, temporary assumptions.
        """
        source = "%s@%s:" % (self.scp_username, hostname)
        return ["scp", "-oStrictHostKeyChecking=no", "-i", self.localsshkeypath, "-r", source]

    def _run_one_cmd(self, args):
        cmd = ' '.join(args)
        self.c.log.debug("command = '%s'" % cmd)
        
        timeout = 10.0 # seconds
        (killed, retcode, stdout, stderr) = \
            child.child(cmd, timeout=timeout)
        
        if killed:
            self.c.log.error("TIMED OUT: '%s'" % cmd)
            return False
        
        if retcode == 0:
            self.c.log.debug("command succeeded: '%s'" % cmd)
            return True
        else:
            errmsg = "problem running command, "
            if retcode < 0:
                errmsg += "killed by signal:"
            if retcode > 0:
                errmsg += "exited non-zero:"
            errmsg += "'%s' ::: return code" % cmd
            errmsg += ": %d ::: error:\n%s\noutput:\n%s" % (retcode, stdout, stderr)
            
            # these commands will commonly fail 
            if self.c.trace:
                self.c.log.debug(errmsg)
            return False

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
        
        
        self.c.log.debug("roles file: '%s'" % services.rolesfile)
        self.c.log.debug("fabtask: '%s'" % fabtask)
        
        args = [services.fablaunch, fabtask, self.ssh_username, self.localsshkeypath, hostname, services.rolesfile]
        
        cmd = ' '.join(args)
        self.c.log.debug("command = '%s'" % cmd)
        
        timeout = 300
        (killed, retcode, stdout, stderr) = \
            child.child(cmd, timeout=timeout)
            
        if killed:
            errmsg = "problem running command, timed out: %s" % cmd
            raise UnexpectedError(errmsg)
            
        if retcode != 0:
            errmsg = "problem running command, "
            if retcode < 0:
                errmsg += "killed by signal:"
            if retcode > 0:
                errmsg += "exited non-zero:"
            errmsg += "'%s' ::: return code" % cmd
            errmsg += ": %d ::: error:\n%s\noutput:\n%s" % (retcode, stderr, stdout)
            raise UnexpectedError(errmsg)
        
    def terminate_ids(self, instanceids):
        con = self._get_connection()
        con.terminate_instances(instanceids)
    
    def filter_by_running(self, vm_list):
        """Filter out any VMs in this list that terminating/terminated"""
        
        ids = []
        vm_map = {}
        for vm in vm_list:
            ids.append(vm.instanceid)
            vm_map[vm.instanceid] = vm
            
        con = self._get_connection()
        self.c.log.debug("querying status of %d instances" % len(ids))
        reservations = con.get_all_instances(instance_ids=ids)
        
        sd = "shutting-down"
        ter = "terminated"
        
        filtered = []
        for res in reservations:
            for inst in res.instances:
                iid = inst.id
                
                if vm_map.has_key(iid):
                    if inst.state == sd:
                        self.c.log.info("Instance %s is %s, filtering" % (iid, sd))
                    elif inst.state == ter:
                        self.c.log.info("Instance %s is %s, filtering" % (iid, ter))
                    else:
                        self.c.log.debug("Instance %s is %s" % (iid, inst.state))
                        filtered.append(vm_map[iid])
                else:
                    stray = "Instance %s is %s (stray in reservation? did you run find-workers?)" % (iid, inst.state)
                    self.c.log.warn(stray)
        
        return filtered
        
    def _get_connection(self):
        # see comments in validate()
        if not self.custom_hostname:
            con = EC2Connection(self.ec2_key, self.ec2_secret)
        else:
            region = RegionInfo(name="nimbus", endpoint=self.custom_hostname)
            if not self.custom_port:
                con =  boto.connect_ec2(self.nimbus_key, self.nimbus_secret,
                                        region=region)
            else:
                con =  boto.connect_ec2(self.nimbus_key, self.nimbus_secret,
                                        port=self.custom_port, region=region) 
        return con
