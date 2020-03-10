# accessocampus
Accessocampus project

Docker:

Build: sudo docker build -t gomme600/accessocampus:latest .

Run server: sudo docker run --name access -d -p 8000:5000 --rm gomme600/accessocampus:latest --server

Run client: sudo docker run --name access -d -p 8000:5000 --rm gomme600/accessocampus:latest --client

Stop: sudo docker stop access

Join: sudo docker exec -u 0 -it <Container ID> /bin/bash
