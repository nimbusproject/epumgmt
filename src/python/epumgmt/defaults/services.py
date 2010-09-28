import os
import simplejson
import string
import tempfile
import time

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

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
        self.rolesfile = None
        self.fablaunch = None
        self.thisrundir = None
        self.userjson = {}

    def validate(self):
        
        action = self.p.get_arg_or_none(ec_args.ACTION)
        if action not in [ACTIONS.CREATE]:
            if self.c.trace:
                self.c.log.debug("validation for services module complete, not a relevant action")
            return
        
        self.servicename = self.p.get_arg_or_none(ec_args.HASERVICE)
        if not self.servicename:
            raise InvalidConfig("service name is required (%s)" % ec_args.HASERVICE.long_syntax)
            
        self.c.log.debug("service name: " + self.servicename)
        
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
            
        self.c.log.debug("fablaunch exe: " + self.fablaunch)
        
        json_vars_path = self.p.get_arg_or_none(ec_args.JSON_VARS)
        if json_vars_path:
            if not os.path.exists(json_vars_path):
                raise InvalidConfig("json file does not exist: %s" % json_vars_path)
            f = open(json_vars_path)
            self.userjson = simplejson.load(f)
            f.close()
        
        run_name = self.p.get_arg_or_none(ec_args.NAME)
        confs_used_dir = self.p.get_conf_or_none("confs_used", "confs_used_dir")
        if not confs_used_dir:
            raise InvalidConfig("There is no confs_used_dir configuration")
        
        if not os.path.isabs(confs_used_dir):
            confs_used_dir = self.c.resolve_var_dir(confs_used_dir)
        
        if not os.path.exists(confs_used_dir):
            raise InvalidConfig("The confs_used_dir does not exist: %s" % confs_used_dir)
        
        self.thisrundir = os.path.join(confs_used_dir, run_name)
        if not os.path.exists(self.thisrundir):
            os.mkdir(self.thisrundir)
            self.c.log.debug("Created a new directory for the exact conf files used for this launch: %s" % self.thisrundir)
        else:
            self.c.log.debug("Directory of exact conf files used for this launch: %s" % self.thisrundir)
        
        self.c.log.debug("chefroles template path: " + self.chefrolespath)
        self.c.log.debug("json for templates: %s" % self.userjson)
        
        self.rolesfile = self.fill_template(self.chefrolespath)
        self.c.log.debug("created roles file: %s" % self.rolesfile)
        
        self.c.log.debug("validated Services module")
        self.validated = True
        
    def fill_template(self, path):
        """Return path to a newly created file which is the result of applying
        variable substitution to the given template file (using keys found in
        the user-supplied json file exclusively).
        
        path -- path to template file
        """
        return self._fill_template(path, self.userjson)
    
    def fill_template_json(self, path, jsondict):
        """Return path to a newly created file which is the result of applying
        variable substitution to the given template file (using keys found in
        given jsondict exclusively).
        
        path -- path to template file
        jsondict -- your variables+values dict
        """
        return self._fill_template(path, jsondict)
    
    def fill_template_bothjson(self, path, jsondict):
        """Return path to a newly created file which is the result of applying
        variable substitution to the given template file (using keys found in
        given jsondict first, falling back to keys found in the user-supplied
        json file).
        
        path -- path to template file
        jsondict -- your variables+values dict
        """
        newjson = {}
        for key in self.userjson.iterkeys():
            newjson[key] = self.userjson[key]
        
        # supplied to method takes precendence:
        for key in jsondict.iterkeys():
            newjson[key] = jsondict[key]
    
        return self._fill_template(path, newjson)
    
    def _fill_template(self, path, jsondict):
        
        if not os.path.exists(path):
            raise InvalidConfig("template file does not exist: %s" % path)
        
        f = open(path)
        doc_tpl = f.read()
        f.close()
            
        template = string.Template(doc_tpl)
        try:
            document = template.substitute(jsondict)
        except KeyError,e:
            extratext = ""
            if len(jsondict.keys()) == 0:
                extratext = "(looks like you did not pass in a json file at all? See --help)"
            raise InvalidConfig("\n\nThe file '%s' has a  variable not present in supplied json: %s\n\nSupplied json %s\n\n%s" % (path, str(e), jsondict, extratext))
        except ValueError,e:
            raise InvalidConfig("The file '%s' has a  bad variable: %s" % (path, str(e)))

        # having the template name in the temp file name makes it easier
        # to identify
        prefix = os.path.basename(path)
        prefix += "_"
        
        (fd, newpath) = tempfile.mkstemp(prefix=prefix, text=True, dir=self.thisrundir)
        
        f = open(newpath, 'w')
        f.write(document)
        f.close()
        
        return newpath

        
        