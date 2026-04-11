FROM docker.io/library/python:3.14

WORKDIR /data

ENTRYPOINT ["python", "-m", "http.server", "8080"]
