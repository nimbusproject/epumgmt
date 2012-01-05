from common import DefaultCommon
from epumgmt.api import RunVM
from parameters import DefaultParameters
from runlogs import DefaultRunlogs
from event_gather import DefaultEventGather
from svc_adapter import DefaultRemoteSvcAdapter
from epu_client import DashiEPUClient

def is_piggybacked(svc_or_id):
    if not svc_or_id:
        return False
    if isinstance(svc_or_id, str):
        instanceid = svc_or_id
    elif isinstance(svc_or_id, RunVM):
        instanceid = svc_or_id.instanceid
    else:
        return False
    if instanceid[0] == 'P':
        return True
    return False
