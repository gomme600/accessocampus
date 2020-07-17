#!/usr/bin/env bash

rm /tmp/.X0-lock &>/dev/null || true

export DISPLAY=:0
export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/host/run/dbus/system_bus_socket
echo "Starting client in 2 seconds"
sleep 2
sudo python3 /usr/src/app/accessocampus/client/loader.py

while :
do
	echo "Starting client failed, so we will just wait here while you debug!"
	sleep 30
done
