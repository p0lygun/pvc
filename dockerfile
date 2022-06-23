FROM python:3.10-slim-buster
RUN apt-get update \
    && apt-get -y install libpq-dev gcc git

WORKDIR /app
COPY . .

RUN pip3 install -r requirements.txt