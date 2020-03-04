FROM python:3.6-alpine



RUN adduser -D microblog



WORKDIR /home/microblog



COPY requirements.txt requirements.txt

# install
RUN apk update && apk add  \
    cmake \
    gcc

RUN python -m venv venv

RUN venv/bin/pip install -r requirements.txt

RUN venv/bin/pip install gunicorn


COPY app app

COPY faces faces

COPY migrations migrations

COPY microblog.py cards.conf app.db config.py boot.sh ./

RUN chmod +x boot.sh



ENV FLASK_APP microblog.py



RUN chown -R microblog:microblog ./

USER microblog



EXPOSE 5000

ENTRYPOINT ["./boot.sh"]


