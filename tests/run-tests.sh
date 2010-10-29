#/bin/bash

# For Nimbus IaaS but also for Context Broker

if [ "X$NIMBUS_KEY" == "X" ]; then
    echo "NIMBUS_KEY must be set"
    exit 1
fi
if [ "X$NIMBUS_SECRET" == "X" ]; then
    echo "NIMBUS_SECRET must be set"
    exit 1
fi
if [ "X$AWS_ACCESS_KEY_ID" == "X" ]; then
    echo "AWS_ACCESS_KEY_ID must be set"
    exit 1
fi
if [ "X$AWS_SECRET_ACCESS_KEY" == "X" ]; then
    echo "AWS_SECRET_ACCESS_KEY must be set"
    exit 1
fi

PYTHON_EXE="/usr/bin/env python"

EPU_HOME_REL="`dirname $0`/.."
export EPUMGMT_HOME=`cd $EPU_HOME_REL; pwd`
NIMBUS_CONTROL_PYLIB="$NIMBUS_CONTROL_DIR/lib/python"
NIMBUS_CONTROL_PYSRC="$NIMBUS_CONTROL_DIR/src/python"
PYTHONPATH="$EPUMGMT_HOME/lib/python:$EPUMGMT_HOME/src/python"
export PYTHONPATH
export EPUMGMT_DB=$EPUMGMT_HOME/epumgmt.db


TESTS_DIR_REL="`dirname $0`"
TESTS_DIR=`cd $TESTS_DIR_REL; pwd`

cd $TESTS_DIR

services_to_test=`cat services.txt`
json_file=`mktemp`
out_file=`mktemp`
pre_running_instances=`mktemp`
export EPU_TEST_VARS=$json_file
rabbit_instance=


failed_tests=""
error_count=0
function on_exit()
{
    echo $json_file
    echo $out_file

    if [ $error_count -ne 0 ]; then
        echo "Errors in $error_count tests"
        echo "    $failed_tests"
    else
        echo "SUCCESS"
    fi
}

trap on_exit EXIT

$PYTHON_EXE ./init_tests.py > $pre_running_instances

echo "running rabbitmq VM on ec2, this may take a bit"
$PYTHON_EXE run_rabbit.py $json_file $EPU_RABBIT_ID | tee $out_file
if [ $PIPESTATUS -ne 0 ]; then   
    echo "first attempt at rabbit failed.  trying again without instance id"
    $PYTHON_EXE run_rabbit.py $json_file | tee $out_file
    if [ $PIPESTATUS -ne 0 ]; then   
        echo "could not start rabbit, sorry"
        exit 1
    fi
fi
rabbit_instance=`tail -n 1 $out_file`
export EPU_RABBIT_ID=$rabbit_instance

echo $rabbit_instance
echo "export EPU_RABBIT_ID=$rabbit_instance" > test_env.sh

cd scripts 
final_rc=0

for service in $services_to_test
do
    export EPU_SERVICE=$service
    if [ "X$1" == "X" ]; then
        for t in *tests.py
        do
            echo "running $t"
            $PYTHON_EXE $t
            if [ $? -ne 0 ]; then
                failed_tests="$t $failed_tests"
                final_rc=1
                error_count=`expr $error_count + 1`
            fi
        done
    else
        echo "running $1"
        $PYTHON_EXE $1
        if [ $? -ne 0 ]; then
            failed_tests="$1 $failed_tests"
            final_rc=1
            error_count=`expr $error_count + 1`
        fi
    fi
done

echo "waiting for clean up time..."
sleep 5
to_kill=`cat $pre_running_instances`
echo "cleaning up [$to_kill]" 

cd $TESTS_DIR
$PYTHON_EXE ./init_tests.py kill $to_kill

echo "$error_count errors"
echo "    $failed_tests"

exit $final_rc
