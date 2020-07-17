# Running the accessocampus client in a container

Build : docker build -f Dockerfile --network=host -t access_v1 .

Run : sudo docker run -it --privileged --entrypoint /bin/bash --net=host --env="DISPLAY" --volume="$HOME/.Xauthority:/root/.Xauthority:rw" access_v1
