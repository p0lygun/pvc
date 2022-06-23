FROM python:3.10-slim-buster
RUN apt-get -y update
RUN apt-get -y install git
WORKDIR /app
COPY . .
RUN pip3 install -r requirements.txt