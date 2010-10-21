from __future__ import with_statement
import os
import sys
from fabric.api import env, run, local, put, cd, hide
from fabric.decorators import runs_once

def bootstrap(rolesfile=None):
    update_dt_data()
    put_chef_data(rolesfile=rolesfile)
    run_chef_solo()

def bootstrap_cei(rolesfile=None):
    put_provisioner_secrets()
    bootstrap(rolesfile=rolesfile)

def put_provisioner_secrets():
    nimbus_key = os.environ.get('NIMBUS_KEY')
    nimbus_secret = os.environ.get('NIMBUS_SECRET')
    if not nimbus_key or not nimbus_secret:
        print "ERROR.  Please export NIMBUS_KEY and NIMBUS_SECRET"
        sys.exit(1)

    ec2_key = os.environ.get('AWS_ACCESS_KEY_ID')
    ec2_secret = os.environ.get('AWS_SECRET_ACCESS_KEY')
    if not ec2_key or not ec2_secret:
        print "ERROR.  Please export AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
        sys.exit(1)

    ensure_opt()
    run("sudo sh -c 'echo export NIMBUS_KEY=%s >> /opt/cei_environment'" % nimbus_key)
    run("sudo sh -c 'echo export AWS_ACCESS_KEY_ID=%s >> /opt/cei_environment'" % ec2_key)
    
    with hide('running'):
        run("sudo sh -c 'echo export NIMBUS_SECRET=%s >> /opt/cei_environment'" % nimbus_secret)
        run("sudo sh -c 'echo export AWS_SECRET_ACCESS_KEY=%s >> /opt/cei_environment'" % ec2_secret)

def update():
    with hide('stdout'):
        run("sudo apt-get -q update")

def update_dt_data():
    # checkout the latest cookbooks:
    with cd("/opt/dt-data"):
        run("sudo git fetch")
        run("sudo git reset --hard origin/HEAD")
    
def put_chef_data(rolesfile=None):
    # put the role and config files:
    put("chefconf.rb", "/tmp/")
    put(rolesfile or "chefroles.json", "/tmp/chefroles.json")
    run("sudo mkdir -p /opt/dt-data/run")
    run("sudo mv /tmp/chefconf.rb /tmp/chefroles.json /opt/dt-data/run/")
        
def run_chef_solo():
    run("sudo chef-solo -l debug -c /opt/dt-data/run/chefconf.rb -j /opt/dt-data/run/chefroles.json")

    
