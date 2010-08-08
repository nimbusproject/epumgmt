import os
from epucontrol.api.exceptions import *
from epucontrol.main import get_all_configs
from epucontrol.main import get_class_by_keyword

def get_parameters(confpath):
    # mini implementation of the dependency injection used in the real program:
    allconfs = get_all_configs(confpath)
    p_cls = get_class_by_keyword("Parameters", allconfigs=allconfs)
    return p_cls(allconfs, None)

def _jump_up_dir(path):
    return "/".join(os.path.dirname(path+"/").split("/")[:-1])

def guess_basedir():
    # figure it out programmatically from location of this source file
    # this can be an unintuitive value
    current = os.path.abspath(__file__)
    while True:
        current = _jump_up_dir(current)
        if os.path.basename(current) == "src":
            # jump up one more time
            current = _jump_up_dir(current)
            return current
        if not os.path.basename(current):
            raise IncompatibleEnvironment("cannot find base directory")

def apply_vardir_maybe(p, var_subdir):
    ret_dir = var_subdir
    if not os.path.isabs(var_subdir):
        # The following is a copy of the logic in Common which is not ideal but
        # we can't instantiate defaults.Common without causing a new log file to
        # be created
        vardir = p.get_conf_or_none("ecdirs", "var")
        if not vardir:
            raise InvalidConfig("There is no wcdirs->var configuration.  This is required.")
            
        if not os.path.isabs(vardir):
            basedir = guess_basedir()
            vardir = os.path.join(basedir, vardir)
            
        ret_dir = os.path.join(vardir, var_subdir)
    
    return ret_dir

def get_user_input(valuename, default=None, required=True):
    answer = None
    question = valuename + (default and ("(%s): " % default) or ": ")
    while not answer:
        value = raw_input(valuename+": ")
        if value:
            answer = value.strip()
        elif default:
            answer = default
        if not answer:
            if required:
                print "Invalid input. You must specify a value. Or hit Ctrl-C to give up."
            else:
                return None

    return answer
