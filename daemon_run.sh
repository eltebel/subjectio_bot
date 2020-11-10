#!/bin/bash
# export PYTHONPATH=$PYTHONPATH:./botski

file_lock="logs/daemon.lock"
file_log="logs/log_console.txt"

CTRL_C_FUN()(
     echo "cleaning up"
     rm $file_lock
     kill $$
 )

[ -e $file_lock ] && echo "lock: $file_lock" && exit
touch $file_lock

trap CTRL_C_FUN 2

while :; do
	python3 daemon.py 2>&1 |tee -a $file_log
	sleep 60
done
