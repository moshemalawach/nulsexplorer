FROM python:3.6-stretch
MAINTAINER Moshe Malawach <moshe.malawach@protonmail.com>

# https://github.com/docker-library/python/issues/13
ENV LANG C.UTF-8

#RUN apt-get update && apt-get install -y -q \
#    python3.6 python3.6-dev python3-pip \
#    ca-certificates

# RUN apt-get install -y -q python3.6 python3.6-dev python3-pymongo python3-crypto python3-regex python3-numpy libffi-dev libxml2-dev libxslt-dev zlib1g-dev libjpeg-dev libfreetype6-dev libcairo2-dev libpango1.0-dev libgdal-dev python3-wheel python3-setuptools

RUN rm -rf /var/lib/apt/lists/*

#RUN /usr/bin/pip install --upgrade pip

RUN /usr/local/bin/pip install --upgrade setuptools

# RUN apt-get install -y -q 

WORKDIR /app

ADD . /app/

RUN /usr/local/bin/pip install -r requirements.txt

RUN /usr/local/bin/python setup.py develop

RUN chmod +x /app/bin/launch.sh

# expose default wsgi port
EXPOSE 8080

CMD ["/bin/bash", "/app/bin/launch.sh"]
