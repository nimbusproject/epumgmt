from fabric.api import run, sudo, put

def setup_and_test_vm(testpgm, postpgm=None):
    if postpgm != None:
        put(postpgm, '/tmp/nimbus_post_barrier')
    sudo('cp -r /home/ubuntu/.ssh /root/')
    put(local_test_pgm, '/tmp/nimbus_test_alive')
    sudo('/tmp/nimbus_test_alive')

def run_posttest_program():
    sudo('/tmp/nimbus_test_alive')
