from epumgmt.api.exceptions import IncompatibleEnvironment, UnexpectedError
from epumgmt.main import em_args
import os

FALSE_POSITIVES = ["site-packages", "python2.5", "python2.6", "bin", "plat-linux2", "app",
                   "lib-old", "lib-tk", "lib-dynload", "lib", "pylib"]

class VersionsNode:
    def __init__(self, vm):
        self.vm = vm
        self.versions = []
        self.gitcommit = None
        self.projectversion = None

def print_versions(p, c, m, run_name):
    vnodes, counts = _gather_vnodes(p, c, m, run_name)
    txt = _vnode_report(vnodes, counts)
    print ""
    print txt
    report_path = p.get_arg_or_none(em_args.WRITE_REPORT)
    if report_path:
        if os.path.exists(report_path):
            raise IncompatibleEnvironment("Can not write report to pre-existing file: %s" % report_path)
        f = open(report_path, mode='w')
        f.write(txt)
        f.close()
        print "Wrote report to: %s" % report_path

def _vnode_report(vnodes, counts):
    if len(vnodes) == 1:
        txt = "Only one source of version information:\n"
        for version in vnodes[0].versions:
            txt += "  %s\n" % version
        if vnodes[0].gitcommit:
            txt += "  GIT: %s" % vnodes[0].gitcommit
        if vnodes[0].projectversion:
            txt += "  Project: %s" % vnodes[0].projectversion
        return txt

    keys = counts.keys()
    keys.sort()
    widest = _widest_key(keys)
    txt = "Versions from %d sources:\n" % len(vnodes)
    for key in keys:
        txt += "  %s %d occurence" % (_pad_txt(key, widest), counts[key])
        if counts[key] != 1:
            txt += "s"
        txt += "\n"

    # Each combination of git + projectversion is treated as a unique package
    # (This guards against any divergence in git commit vs. manual version bump.)
    appv = {}
    for vnode in vnodes:
        tup = (vnode.projectversion, vnode.gitcommit)
        if appv.has_key(tup):
            appv[tup] += 1
        else:
            appv[tup] = 1

    keys = appv.keys()
    keys.sort()
    toprints = []
    for key in keys:
        toprints.append("%s (git: %s)" % (key[0], key[1]))

    widest = _widest_key(toprints)
    txt += "\n\nApp versions from %d sources:\n" % len(vnodes)
    for key in keys:
        toprint = "%s (git: %s)" % (key[0], key[1])
        txt += "  %s %d occurence" % (_pad_txt(toprint, widest), appv[key])
        if appv[key] != 1:
            txt += "s"
        txt += "\n"

    return txt

def _widest_key(keys):
    widest = 0
    for key in keys:
        if len(key) > widest:
            widest = len(key)
    return widest

def _pad_txt(txt, widest):
    if len(txt) >= widest:
        return txt
    difference = widest - len(txt)
    while difference:
        txt += " "
        difference -= 1
    return txt


def _gather_vnodes(p, c, m, run_name):
    c.log.debug("Looking for versions")

    allvms = m.persistence.get_run_vms_or_none(run_name)
    if not allvms or len(allvms) == 0:
        raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s'" % run_name)

    vnodes = _init_vnodes(allvms)
    vlen = len(vnodes)
    if not vlen:
        raise IncompatibleEnvironment("Could not find any version information")
    elif vlen == 1:
        c.log.debug("Found version information from 1 source")
    else:
        c.log.debug("Found version information from %d sources" % vlen)

    counts = {}
    for vnode in vnodes:
        for version in vnode.versions:
            if counts.has_key(version):
                counts[version] += 1
            else:
                counts[version] = 1
    return vnodes, counts

def _init_vnodes(allvms):
    vnodes = []
    for vm in allvms:
        for ev in vm.events:
            if ev.name == "deplist":
                vnode = VersionsNode(vm)
                vnodes.append(vnode)
                if not ev.extra:
                    raise UnexpectedError("deplist event syntax is not right")
                #print "DEPLIST EXTRA: %s" % ev.extra
                for key in ev.extra.keys():
                    if key == "depsource":
                        continue
                    elif key == "gitcommit":
                        vnode.gitcommit = ev.extra[key]
                    elif key == "projectversion":
                        vnode.projectversion = ev.extra[key]
                    elif key.startswith("dep"):
                        dep = _filter_dep(ev.extra[key])
                        if dep:
                            vnode.versions.append(dep)
    return vnodes

def _filter_dep(dep):
    if not dep:
        return None
    dep = dep.strip()
    if not dep:
        return None
    if dep in FALSE_POSITIVES:
        return None
    if dep.endswith(".pom"):
        return None
    if dep.endswith(".xml"):
        return None
    if dep.endswith(".properties"):
        return None
    return dep
