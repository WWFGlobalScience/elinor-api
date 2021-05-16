FROM honeycrisp/docker:django-geo-api

RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client-13

ADD ./requirements.txt requirements.txt
RUN pip install --upgrade -r requirements.txt
RUN rm requirements.txt

WORKDIR /var/projects/webapp
ADD ./src .

EXPOSE 80 8000 443
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
