import os
import time
from epucontrol.api.exceptions import *
import epucontrol.main.ec_args as ec_args
from epucontrol.main import ACTIONS

class DefaultServices:
    
    def __init__(self, params, common):
        self.p = params
        self.c = common
        self.validated = False
        self.servicename = None
        self.chefrolespath = None
        self.fablaunch = None

    def validate(self):
        
        action = self.p.get_arg_or_none(ec_args.ACTION)
        if action not in [ACTIONS.CREATE]:
            if self.c.trace:
                self.c.log.debug("validation for services module complete, not a relevant action")
            return
        
        self.servicename = self.p.get_arg_or_none(ec_args.HASERVICE)
        if not self.servicename:
            raise InvalidConfig("service name is required (%s)" % ec_args.HASERVICE.long_syntax)
        
        chefroles = self.p.get_conf_or_none(self.servicename, "chefroles")
        if not chefroles:
            raise InvalidConfig("expecting a 'chefroles' configuration in a conf section named '%s', see services.conf file" % self.servicename)
        
        if not os.path.isabs(chefroles):
            self.chefrolespath = self.c.resolve_serviceconf_dir(chefroles)
        else:
            self.chefrolespath = chefroles
        
        if not os.path.exists(self.chefrolespath):
            raise InvalidConfig("chefroles file does not exist: %s" % self.chefrolespath)
            
        fablaunch = self.p.get_conf_or_none("fablaunch", "fablaunch")
        if not fablaunch:
            raise InvalidConfig("expecting a 'fablaunch' configuration in a conf section named 'fablaunch', see services.conf file")
        if not os.path.isabs(fablaunch):
            self.fablaunch = self.c.resolve_libexec_dir(fablaunch)
        else:
            self.fablaunch = fablaunch
        
        self.validated = True
        self.c.log.debug("service name: " + self.servicename)
        self.c.log.debug("chefroles path: " + self.chefrolespath)
        self.c.log.debug("fablaunch exe: " + self.fablaunch)
        self.c.log.debug("validated Services module")

