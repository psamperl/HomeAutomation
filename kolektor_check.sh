#!/bin/bash

# Script watches if collector process is running.
# If not then starts it and sends message to Pushbullet

TOKEN=$1
if ps -ef | grep -v grep | grep kolektor.py ; then
        exit 0
else
        /usr/bin/python /home/pi/HomeAutomation/kolektor.py &>/dev/null
		/usr/bin/curl -u $TOKEN: https://api.pushbullet.com/v2/pushes -d type=note -d title="Alert" -d body="Restarting kolektor.py!" &>/dev/null
fi
