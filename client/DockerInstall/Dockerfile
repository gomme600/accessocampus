FROM balenalib/raspberrypi3:buster

# Install desktop environment
RUN install_packages xserver-xorg-core \
    xinit lxsession desktop-file-utils \
    raspberrypi-ui-mods rpd-icons \
    gtk2-engines-clearlookspix \
    matchbox-keyboard

# disable lxpolkit popup warning
RUN mv /usr/bin/lxpolkit /usr/bin/lxpolkit.bak

RUN echo "#!/bin/bash" > /etc/X11/xinit/xserverrc \
  && echo "" >> /etc/X11/xinit/xserverrc \
  && echo 'exec /usr/bin/X -s 0 dpms -nolisten tcp "$@"' >> /etc/X11/xinit/xserverrc

# Setting working directory
WORKDIR /usr/src/app/accessocampus/client

COPY start.sh start.sh

RUN chmod +x start.sh

RUN install_packages git \
    python3-pip libatlas-base-dev libhdf5-dev \
    libhdf5-serial-dev libatlas-base-dev \
    libjasper-dev libqtgui4 libqt4-test \
    python3-pyqt5 apt-utils python3-setuptools \
    v4l-utils python-opencv python-numpy

RUN git clone https://github.com/gomme600/accessocampus.git

WORKDIR /usr/src/app/accessocampus/client

RUN pip3 install -r requirements.txt

RUN git clone https://github.com/groupgets/pylepton.git

WORKDIR /usr/src/app/accessocampus/client/pylepton

RUN python3 setup.py install

WORKDIR /usr/src/app/accessocampus/client

RUN mv pylepton pylepton_install

WORKDIR /usr/src/app/accessocampus/client

# Adding things to autostart will cause them to be launchd automatically on starup
# COPY autostart /etc/xdg/lxsession/LXDE-pi/autostart

ENV UDEV=1

CMD ["bash", "start.sh"]
