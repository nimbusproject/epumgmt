import em_args
from epumgmt.api.exceptions import InvalidInput, UnexpectedError

def reconfigure_n(p, c, m, run_name, cloudinitd):
    """Send an EPU Controller reconfigure message to an engine that is presumed to be NPreservingEngine or similar
    """

    arg = em_args.NEWN.long_syntax
    new_n = p.get_arg_or_none(em_args.NEWN)
    if not new_n:
        raise InvalidInput("The %s argument is required for this" % arg)

    m.remote_svc_adapter.initialize(m, run_name, cloudinitd)
    if not m.remote_svc_adapter.is_channel_open():
        c.log.warn("Cannot reconfigure: there is no channel open to the EPU controllers")
        return

    tasks = new_n.split(",")
    for task in tasks:
        parts = task.split(":")
        if len(parts) != 2:
            raise InvalidInput("The %s argument requires a particular syntax, see help. This is bad: %s" % (arg, task))
        _do_one_reconfigure_n(m, parts[0], parts[1])

def _do_one_reconfigure_n(m, controller, newn):
    """Should be in parallel someday (could be better with a different channel to services altogether)
    """
    if not m.remote_svc_adapter.reconfigure_n(controller, newn):
        raise UnexpectedError("Problem reconfiguring controller '%s" % controller)
