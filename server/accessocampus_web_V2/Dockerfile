FROM debian:latest

# set a directory for the app
WORKDIR /usr/src/app

# copy all the files to the container
COPY . .

# install
RUN apt-get update && apt-get install -y \
    python3-pyqt5 \
    python3-pip \
    python3 \
    cmake
    

# install dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# tell the port number the container should expose
EXPOSE 5000

# run the command
CMD ["export FLASK_APP=microblog.py"]

# run the command
CMD ["flask run"]
