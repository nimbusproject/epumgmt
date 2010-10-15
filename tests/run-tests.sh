#/bin/bash

PYTHON_EXE="/usr/bin/env python"

EPU_HOME_REL="`dirname $0`/.."
export EPUMGMT_HOME=`cd $EPU_HOME_REL; pwd`
NIMBUS_CONTROL_PYLIB="$NIMBUS_CONTROL_DIR/lib/python"
NIMBUS_CONTROL_PYSRC="$NIMBUS_CONTROL_DIR/src/python"
PYTHONPATH="$EPUMGMT_HOME/lib/python:$EPUMGMT_HOME/src/python"
export PYTHONPATH


TESTS_DIR_REL="`dirname $0`"
TESTS_DIR=`cd $TESTS_DIR_REL; pwd`

cd $TESTS_DIR

json_file=`mktemp`
out_file=`mktemp`
export EPU_TEST_VARS=$json_file
rabbit_instance=

function on_exit()
{
    rm -f $json_file
    rm -f $out_file
}

trap on_exit EXIT


echo "running rabbitmq VM on ec2, this may take a bit"
./run_rabbit.py $json_file $EPU_RABBIT_ID | tee $out_file
if [ $PIPESTATUS -ne 0 ]; then   
    echo "first attempt at rabbit failed.  trying again without instance id"
    ./run_rabbit.py $json_file | tee $out_file
    if [ $PIPESTATUS -ne 0 ]; then   
        echo "could not start rabbit, sorry"
        exit 1
    fi
fi
rabbit_instance=`tail -n 1 $out_file`
export EPU_RABBIT_ID=$rabbit_instance

echo $rabbit_instance
echo "export EPU_RABBIT_ID=$rabbit_instance" > test_env.sh

failed_tests=""
error_count=0
cd scripts 
final_rc=0
for t in *tests.py
do
    $PYTHON_EXE $t
    if [ $? -ne 0 ]; then
        failed_tests="$t $failed_tests"
        final_rc=1
        error_count=`expr $error_count + 1`
    fi
done
#nosetests *tests.py

echo "$error_count errors"
echo "\t$failed_tests"

exit $final_rc
