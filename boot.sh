#!/bin/bash
# this script is used to boot a Docker container
source venv/bin/activate

if [ $1 = "--server" ]
then
        echo "Starting server !"
        /bin/bash server/dockerserver/boot-server.sh
fi

if [ $1 = "--client" ]
then
        echo "Starting client !"
        DISPLAY=:0 python3 client/dockerclient/loader.py
fi


