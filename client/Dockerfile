FROM yummygooey/raspbian-buster:latest



#RUN adduser -D accessocampus



WORKDIR /home/accessocampus



COPY requirements.txt requirements.txt

# install
RUN apt-get update && apt-get install -y \
    cmake \
    gcc \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv

RUN python3 -m venv venv

RUN pip3 install -r requirements.txt

#RUN venv/bin/pip install gunicorn


COPY accessocampus_ressources accessocampus_ressources

COPY py532lib py532lib

COPY quick2wire quick2wire

COPY accessocampus_GUI_rc.py haarcascade_frontalface_default.xml GUI.ui cards.conf loader.py boot.sh ./

RUN chmod +x boot.sh



#ENV FLASK_APP microblog.py



#RUN chown -R microblog:microblog ./

#USER accessocampus



EXPOSE 5000

ENTRYPOINT ["./boot.sh"]


