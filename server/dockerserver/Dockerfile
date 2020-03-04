FROM python:3.6-alpine

RUN adduser -D microblog

WORKDIR /home/microblog

RUN apk add build-base python-dev py-pip jpeg-dev zlib-dev

ENV LIBRARY_PATH=/lib:/usr/lib

RUN python -m pip install -U --force-reinstall pip

RUN apk update

RUN apk add make automake gcc g++ subversion python3-dev cmake

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn pymysql

COPY app app
COPY migrations migrations
COPY faces faces
COPY microblog.py accessocampus_full_mqtt_server_web.py config.py boot.sh ./
RUN chmod a+x boot.sh

ENV FLASK_APP microblog.py

RUN chown -R microblog:microblog ./
USER microblog

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
