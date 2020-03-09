#!/bin/sh
# this script is used to boot a Docker container
source venv/bin/activate
DISPLAY=:0 python3 loader.py
