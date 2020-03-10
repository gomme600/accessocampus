#!/bin/bash
# this script is used to boot a Docker container

cd $(dirname $0)

if [ $1 = "--server" ]
then
        echo "Starting server !"
        cd server/dockerserver/
        /bin/bash boot-server.sh
fi

if [ $1 = "--client" ]
then
        echo "Starting client !"
        cd client/dockerclient/
        DISPLAY=:0 python3 loader.py
fi


