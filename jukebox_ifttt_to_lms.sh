#!/bin/bash
dir=`dirname $0`
log="/var/log/jukebox_ifttt_to_lms.service.log"
if [ "$1" == "start" ]; then
	nohup $dir/jukebox_ifttt_to_lms.py > $log 2>&1 &
elif [ "$1" == "stop" ]; then
	pkill -f 'python3.*jukebox_ifttt_to_lms.py'
elif [ "$1" == "status" ]; then
	pgrep -a -f 'python3.*jukebox_ifttt_to_lms.py'
else
	echo "usage: $0 start|stop|status" >&2
	exit 1
fi
