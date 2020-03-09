FROM debian:latest

#RUN adduser -D accessocampus
RUN useradd -ms /bin/bash accessocampus

WORKDIR /home/accessocampus

RUN apt-get update

RUN apt-get install -y python3-dev python3-pip python3-dev python3-venv git

ENV LIBRARY_PATH=/lib:/usr/lib

RUN python3 -m pip install -U --force-reinstall pip

RUN apt-get install -y make automake gcc g++ subversion cmake

COPY requirements.txt requirements.txt
#RUN python3 -m venv venv
#RUN venv/bin/pip3 install wheel
#RUN venv/bin/pip3 install -r requirements.txt
#RUN venv/bin/pip3 install gunicorn pymysql

RUN pip3 install wheel
RUN pip3 install -r requirements.txt
RUN pip3 install gunicorn pymysql

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
USER accessocampus

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
CMD [" --server"]
