# To launch client in various scenarii #
Launch in a TMUX session !

## Debug mode ##
rm -f /tmp/sensocampus.log
export DISPLAY=':0.0'; export LXDE_USER_HOME_DIR="/home/pi"; ./client.py -d 2>&1 | tee -a /tmp/sensocampus.log

## Normal mode ##
export DISPLAY=':0.0'; export LXDE_USER_HOME_DIR="/home/pi"; ./client.py

