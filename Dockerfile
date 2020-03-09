FROM debian:latest

RUN adduser -D accessocampus

WORKDIR /home/accessocampus

RUN apt-get install -y build-base python3-dev jpeg-dev zlib-dev python3-pip python3-dev python3-venv

ENV LIBRARY_PATH=/lib:/usr/lib

RUN python -m pip install -U --force-reinstall pip

RUN apt-get update

RUN apt-get install -y make automake gcc g++ subversion cmake

COPY requirements.txt requirements.txt
RUN python3 -m venv venv
RUN venv/bin/pip3 install -r requirements.txt
RUN venv/bin/pip3 install gunicorn pymysql

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
