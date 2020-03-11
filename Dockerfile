FROM debian:latest

#RUN adduser -D accessocampus
RUN useradd -ms /bin/bash accessocampus

WORKDIR /home/accessocampus

RUN apt-get update

RUN apt-get install -y python3-dev python3-pip python3-dev python3-venv git

ENV LIBRARY_PATH=/lib:/usr/lib

RUN python3 -m pip install -U --force-reinstall pip

RUN apt-get install -y make automake gcc g++ subversion cmake

RUN apt-get install -y libtiff5-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev libharfbuzz-dev libfribidi-dev tcl8.6-dev tk8.6-dev python-tk

COPY requirements.txt requirements.txt
#RUN python3 -m venv venv
#RUN venv/bin/pip3 install wheel
#RUN venv/bin/pip3 install -r requirements.txt
#RUN venv/bin/pip3 install gunicorn pymysql

RUN pip3 install wheel
RUN pip3 install --extra-index-url=https://www.piwheels.org/simple opencv-contrib-python==4.1.0.25
RUN pip3 install -r requirements.txt
RUN pip3 install gunicorn pymysql

RUN apt-get install -y libatlas-base-dev libqtgui4 libqt4-test

RUN wget http://ftp.br.debian.org/debian/pool/main/j/jasper/libjasper-dev_1.900.1-debian1-2.4+deb8u3_armhf.deb
RUN wget http://ftp.br.debian.org/debian/pool/main/j/jasper/libjasper1_1.900.1-debian1-2.4+deb8u3_armhf.deb
RUN wget http://ftp.br.debian.org/debian/pool/main/g/glibc/multiarch-support_2.19-18+deb8u10_armhf.deb
RUN dpkg -i multiarch-support_2.19-18+deb8u10_armhf.deb
RUN dpkg -i libjasper1_1.900.1-debian1-2.4+deb8u3_armhf.deb
RUN dpkg -i libjasper-dev_1.900.1-debian1-2.4+deb8u3_armhf.deb

pip3 install --extra-index-url=https://www.piwheels.org/simple opencv-contrib-python==3.4.3.18

RUN git clone https://github.com/gomme600/pylepton.git
WORKDIR /home/accessocampus/pylepton
RUN python3 setup.py install
WORKDIR /home/accessocampus

COPY client client
COPY server server
COPY deploy-tests.sh boot.sh ./
RUN chmod a+x boot.sh
RUN chmod a+x deploy-tests.sh

ENV FLASK_APP microblog.py

#RUN chown -R microblog:microblog ./
#USER accessocampus

RUN apt-get install -y libsm6 libxext6 libxrender-dev python3-pyqt5

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
CMD [" "]
