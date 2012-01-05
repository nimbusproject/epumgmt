==============================================================================

See the documentation here: http://...

==============================================================================

NOTE: This README and the online documentation discusses *our use* of
cloudinit.d, we use it in a particular pattern with particular tools (for
example, Chef, which is not required).  If you want to do something
differently, there is usually a way to make it happen.

==============================================================================

I. Quick guide for the impatient:

Export the following environment variables into your shell:

Export the following environment variables into your shell:

    # Credentials for Nimbus
    export CTXBROKER_KEY=`cat ~/.secrets/CTXBROKER_KEY`
    export CTXBROKER_SECRET=`cat ~/.secrets/CTXBROKER_SECRET`
    export NIMBUS_KEY=`cat ~/.secrets/NIMBUS_KEY`
    export NIMBUS_SECRET=`cat ~/.secrets/NIMBUS_SECRET`
    
    # Credentials for EC2
    # The provisioner uses to start worker nodes on EC2 in some situations
    export AWS_ACCESS_KEY_ID=`cat ~/.secrets/AWS_ACCESS_KEY_ID`
    export AWS_SECRET_ACCESS_KEY=`cat ~/.secrets/AWS_SECRET_ACCESS_KEY`
    
    # Credentials for cloudinit.d itself
    # cloudinit.d uses to start the base nodes
    export CLOUDBOOT_IAAS_ACCESS_KEY="$AWS_ACCESS_KEY_ID"
    export CLOUDBOOT_IAAS_SECRET_KEY="$AWS_SECRET_ACCESS_KEY"
    
    # Credentials for Cassandra
    # You make these up
    export CASSANDRA_USERNAME="mamacass"
    export CASSANDRA_PASSWORD=`uuidgen`
    
    # Credentials for RabbitMQ
    # You make these up
    export RABBITMQ_USERNAME="easterbunny"
    export RABBITMQ_PASSWORD=`uuidgen`
    
    # If you are running your own Cassandra instance outside the launch
    # plan, this HAS to change every launch.
    export EXCHANGE_SCOPE="sysname123"

Run:

   RUN_NAME = "my_run_name"
   if [ -n $EXCHANGE_SCOPE ]; then
     RUN_NAME=$EXCHANGE_SCOPE
   fi
   cloudinitd boot main.conf -v -v -v -l debug -x -n $RUN_NAME
   
Inspect:

   epumgmt -a status -n $RUN_NAME
   
==============================================================================

II. For launch plan authors: conventions

There are three layers of value substitutions to understand.

1. The "deps.conf" files (and "deps-common.conf") contain key/value pairs.
   
   There are two kinds of values.  Examples:
   
      1A. Literal
      epu_git_repo: https://github.com/ooici/epu.git
   
      1B. Variable
      broker_ip_address: ${basenode.hostname}
     
   In the literal kind, you have a straight string value.
   
   In the variable kind, you are telling cloudinit.d that a service called
   "x" provides a dynamic value from the launch (in this example, a service
   called "basenode" provides "hostname" -- when this key "broker_ip_address"
   is desired later, cloudinit.d will provide the hostname value from wherever
   the "svc-basenode" service ended up).

2. Then there are the json files.

   These are configuration files for chef-solo that are run on the VM instances
   that get started.  These files are more complicated than simple key/value,
   but there is the same idea present: some values are literal, others obtained
   via substitution.

   Any substitution here comes from the *deps files*.  For example, if you list
   "${broker_ip_address}", the value will come from the dep file containing that
   key.  For each service you can explicitly list which deps files are "in play"
   for that substitution.
   
   For every cloudinit.d launch, temporary files are created with all of the
   substitutions enacted.  These files are what get transferred to the VM and
   serve as input to the boot-time contextualization program: in our case this
   is chef-solo.
   
3. The third and final layer of substitution is in the chef recipes themselves.
   These recipes make references to variables in the json files.  These json
   files are sent to the node as literal configuration files.  You can always
   debug a chef recipe by looking at the configuration file that is given to
   chef-solo and finding the exact string value that was in play.

==============================================================================

III. For launch plan authors: chef json files

Rules for the bootconf json files when using the main recipe "X" which is
what we use most of the time.

* appretrieve:retrieve_method

  This can have the value 'archive' or 'git'.
  
  When it is 'archive', the file configured at "appretrieve:archive_url" is
  retrieved over http and it is assumed to be a tar.gz archive.
  
  When it is 'git', the following configurations are used:
  * appretrieve:git_repo
  * appretrieve:git_branch
  * appretrieve:git_commit
  
  Note that those are the controls for the "thing installed".
  
  All subsequent dependency resolution happens via the dependency lists that
  come as part of that installation -- by way of the server listed in the
  "appinstall:package_repo" configuration.
  
* appinstall:package_repo

  The "thing installed" has a dependency list and this package repository
  configuration is what is used during the installation process to resolve
  the dependencies.

* appinstall:install_method

  This can have the following values:
  
  * py_venv_setup
    Create a new virtualenv, install using "python setup.py install"

  * py_venv_buildout
    Create a new virtualenv, install using "bootstrap.py" and "bin/buildout"
    
  * Future: more options for "burned" setups.
    
* apprun:run_method

  This can have the following values:

  * sh
    The old default, create a shell script for each service listed in the
    "services" section in the json file.  Then start that shell script (unless
    the service is also listed in the "do_not_start" section, for an example
    see the provisioner.json file).
    
  * supervised
    The new default, each service listed in the "services" section in the json
    file is watched by a supervisor process.  This will monitor the unix process
    and communicate failures off of the machine.
    
    
    
  
==============================================================================



