#!/bin/bash

cd /home/basenode/app
sudo -u basenode /home/basenode/app/scripts/run_under_env.sh /home/basenode/app-venv/bin/activate epu-cassandra-schema
