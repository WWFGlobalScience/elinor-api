# Elinor API

[![Deploy app to AWS Elastic Beanstalk](https://github.com/WWFGlobalScience/elinor-api/actions/workflows/deploy.yml/badge.svg)](https://github.com/WWFGlobalScience/elinor-api/actions/workflows/deploy.yml)

## Stack

- [Django](https://www.djangoproject.com/) (Python)
- [Gunicorn](https://gunicorn.org/) (wsgi)
- [Nginx](https://www.nginx.com/) (webserver)
- [Supervisor](http://supervisord.org/) (process control)
- [Debian](https://www.debian.org/releases/stretch/) (OS)
- [Docker](https://www.docker.com/) (container)

## Local Development Workflow

Common workflow tasks are wrapped up using [Fabric](http://www.fabfile.org/) commands. Refer to `fabfile.py` for the
current commands. Add commands as required.

## Local Development Setup

### Installation

This project uses Docker for configuring the development environment and managing it. By overriding the container's
environment variables, the same Docker image can be used for the production service. Thus, for development work, you
must have Docker installed and running. You will also need a local Python environment; some kind of virtualization is recommended (e.g. [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv)), in which you should run `pip install --upgrade -r requirements_dev.txt`.

Note that the following covers only local configuration, not deployment. Nevertheless, see the directories outside of
`src` for how we deploy to [Elastic Beanstalk](https://aws.amazon.com/elasticbeanstalk/) using
[CircleCI](https://circleci.com/) and [Docker Hub](https://hub.docker.com/).

#### Environment variables

The following are the redacted key-val pairs for a local Elinor `.env` file or for Elastic Beanstalk configuration
settings:

```
ENV=local
ADMINS=
ALLOWED_HOSTS=
DB_HOST=elinor_db
DB_NAME=elinor
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=api_db
DB_PORT=5432
PGPASSWORD=postgres
AWS_BACKUP_BUCKET=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
AWS_STORAGE_BUCKET_NAME=
EMAIL_HOST=
EMAIL_PORT=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
RESTORE=local
BACKUP=local
DJANGO_SECRET_KEY=
```

#### Local environment intialization

Once Docker is installed and local environment variables set, run the following:

```sh
$ fab buildnocache
$ fab up
```

If this is the first time running the up command, the api image will be built and postgis image will be downloaded. Then
the containers will be started.

With a database already created and persisted in an S3 bucket via

```sh
$ fab dbbackup
``` 
,

```sh
$ fab dbrestore
``` 

will recreate and populate the local database with the latest dump. Without the S3 dump (i.e. running for the first
time), you'll need to create a local database and then run

 ```sh
$ fab migrate
``` 

to create its schema.

A shortcut for the above steps, once S3 is set up, is available via:

```
$ fab freshinstall:[env]

env: local (default), dev, prod
```

### Running the Webserver

Once everything is installed, run the following to have the API server running in the background:

```sh
$ fab runserver
```

### Further

The project directory `api` is mounted to the container, so any changes you make outside the container (e.g. using an
IDE installed on your host OS) are available inside the container.

Please note that running `fab up` does NOT rebuild the image. So if you are making changes to the Dockerfile, for
example adding a dependency to the `requirement.txt` file, you will need to do the following:

```
$ fab down  // Stops and Removes the containers
$ fab build  // Builds a new image
$ fab up
```

> Note: this will delete your local database; all data will be lost.

### Database commands

```
$ fab dbbackup:<env>

env: local, dev, prod
```

Backup the database from a named S3 key

```
$ fab dbrestore:<env>

env: local, dev, prod
```

### Translation support

To add a language:
- determine correct code and spelling ([ISO 639.2](https://www.loc.gov/standards/iso639-2/php/code_list.php) standard suggested)
- add to settings.LANGUAGES
- makemigrations and migrate

To make a newly added language available from the `/activelanguages/` API endpoint:
- in Django Admin, go to `Active languages` (`/admin/api/activelanguage/`)
- click `Sync languages` button in upper right, then click button on following page
- click language to edit details, check `Active` checkbox, and save

To add model/field for translation:
- add to translation.py
- makemigrations and migrate
- run update_translation_fields to copy existing base value to default-language field versions (e.g. name -> name_en)
- alter admin to mixin TranslationAdmin
