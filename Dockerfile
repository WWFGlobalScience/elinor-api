FROM python:3.10-slim-bullseye
LABEL maintenance="admin@elinordata.org"

ENV DEBIAN_FRONTEND noninteractive
ENV LANG C.UTF-8
ENV LANGUAGE C.UTF-8
ENV LC_ALL C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg \
    build-essential \
    libpq-dev \
    python3-dev \
    wget \
    vim \
    nano \
    supervisor \
    nginx \
    gunicorn \
    postgresql-client-13 \
    gdal-bin \
    python3-gdal

RUN pip install --upgrade pip
ADD ./requirements.txt requirements.txt
RUN pip install --upgrade -r requirements.txt
RUN rm requirements.txt

RUN groupadd webapps
RUN useradd webapp -G webapps
RUN mkdir -p /var/log/webapp/ && chown -R webapp /var/log/webapp/ && chmod -R u+rX /var/log/webapp/
RUN mkdir -p /var/run/webapp/ && chown -R webapp /var/run/webapp/ && chmod -R u+rX /var/run/webapp/
RUN mkdir -p /tmp/webapp/ && chown -R webapp /tmp/webapp/ && chmod -R u+rX /tmp/webapp/
ADD ./config/gunicorn.conf /

RUN rm /etc/nginx/sites-enabled/default && rm /etc/nginx/sites-available/default
ADD ./config/webapp.nginxconf /etc/nginx/sites-enabled/

RUN mkdir -p /var/log/supervisor
ADD ./config/supervisor_conf.d/*.conf /etc/supervisor/conf.d/

WORKDIR /var/projects/webapp
ADD ./src .

EXPOSE 80 8000 443
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
