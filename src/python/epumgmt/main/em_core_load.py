import em_args
import os
from epumgmt.defaults import cloudinitd_load

def get_cloudinit(p, c, m, run_name):
    """Get cloudinit.d API handle.  Loads any new EPU related services in the process.
    """
    return cloudinitd_load.load(p, c, m, run_name, _find_dbdir(p))

def load(p, c, m, run_name, silent=False):
    """Load any EPU related instances from a local cloudinit.d launch with the same run name.
    """
    cloudinitd_load.load(p, c, m, run_name, _find_dbdir(p), silent=silent)

def _find_dbdir(p):
    ci_path = p.get_arg_or_none(em_args.CLOUDINITD_DIR)
    if not ci_path:
        ci_path = os.path.expanduser("~/.cloudinitd")
    return ci_path
