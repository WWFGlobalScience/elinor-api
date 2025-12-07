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

Common workflow tasks are wrapped up using [make](https://man7.org/linux/man-pages/man1/make.1.html) commands. Refer to `Makefile` for the current commands, and see examples below.

## Local Development Setup

### Installation

This project uses Docker for configuring the development environment and managing it. By overriding the container's
environment variables, the same Docker image can be used for the production service. Thus, for development work, you
must have Docker installed and running.

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

```
$ make buildnocache
$ make up
```

If this is the first time running the up command, the api image will be built and postgis image will be downloaded. Then
the containers will be started.

With a database already created and persisted in an S3 bucket via

```
$ make dbbackup
``` 
,

```
$ make dbrestore
``` 

will recreate and populate the local database with the latest dump. Without the S3 dump (i.e. running for the first
time), you'll need to create a local database and then run

 ```
$ make migrate
``` 

to create its schema.

A shortcut for the above steps, once S3 is set up, is available via:

```
$ make freshinstall:[env]

env: local (default), dev, prod
```

### Running the Webserver

Once everything is installed, run the following to have the API development server running in the background:

```
$ make runserver
```

### Further

The project directory `api` is mounted to the container, so any changes you make outside the container (e.g. using an
IDE installed on your host OS) are available inside the container.

Please note that running `make up` does NOT rebuild the image. So if you are making changes to the Dockerfile, for
example adding a dependency to the `requirement.txt` file, you will need to do the following:

```
$ make down  // Stops and Removes the containers
$ make build  // Builds a new image
$ make up
```

> Note: this will delete your local database; all data will be lost.

### Database commands

```
$ make dbbackup:<env>

env: local (default), dev, prod
```

Backup the database from a named S3 key

```
$ make dbrestore:<env>

env: local (default), dev, prod
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

## Deployment

This project uses automated deployment to AWS Elastic Beanstalk via GitHub Actions. The deployment process is triggered by pushes to specific branches or tags.

### Deployment Environments

- **Development (dev)**: Automatically deploys when changes are merged to the `dev` branch
- **Production (prod)**: Automatically deploys when a version tag is pushed (e.g., `v1.2.3`)

### Deployment Process

#### Development Deployment

1. Create a pull request with your changes
2. After review and approval, merge the PR into the `dev` branch
3. The GitHub Action automatically:
   - Builds a Docker image from the latest code
   - Pushes the image to GitHub Container Registry (tagged as `dev`)
   - Creates an Elastic Beanstalk application version
   - Updates the `elinor-dev` environment with the new version
   - Runs post-deployment hooks (see below)

#### Production Deployment

1. Ensure all changes are QAd in the dev environment
2. Merge `dev` into `main` (comprising one or more feature branches that were merged into `dev`)
3. Create and push a version tag following semantic versioning:
   ```
   $ git tag v1.2.3
   $ git push origin v1.2.3
   ```
4. The GitHub Action automatically:
   - Builds a Docker image from the tagged commit
   - Pushes the image to GitHub Container Registry (tagged as `prod`)
   - Creates an Elastic Beanstalk application version
   - Updates the `elinor-prod` environment with the new version
   - Runs post-deployment hooks (see below)

### Post-Deployment Hooks

After each deployment, Elastic Beanstalk automatically runs the following commands inside the container (defined in `.platform/hooks/postdeploy/99_delayed_commands.sh`):

1. `python manage.py dbbackup` - Backs up the database to S3
2. `python manage.py collectstatic --noinput` - Collects static files
3. `python manage.py migrate --noinput` - Applies any pending database migrations
4. `supervisorctl restart all` - Restarts all services

### Database Migrations

**Important**: Database migrations are applied automatically during deployment. When you add a migration (e.g., to add a new language to `settings.LANGUAGES`):

1. Create the migration locally:
   ```
   $ make makemigrations
   ```
2. Commit the migration file to your branch
3. Create a pull request and merge to `dev` (or push a tag for production)
4. During deployment, the GitHub Action will automatically run `python manage.py migrate --noinput` via the post-deployment hook
5. The migration will be applied to the database, just like any other code change

You do not need to manually run migrations on the server. The deployment process handles this automatically.

### Monitoring Deployments

- View deployment status in the [GitHub Actions tab](https://github.com/WWFGlobalScience/elinor-api/actions/workflows/deploy.yml)
- Check Elastic Beanstalk environment health in the AWS Console
- Review application logs via Elastic Beanstalk or CloudWatch

## Accessing Deployed Code and Database

### SSH Access

During normal operations, accessing the command line on a deployed environment (dev or prod) shouldn't be necessary. However, if you need to troubleshoot a problem or run a one-off command, you can access the EC2 instance via SSH:

1. Go to the [AWS Console EC2 Instances page](https://console.aws.amazon.com/ec2/v2/home#Instances)
2. Select the appropriate running EC2 instance
3. Click the **Connect** button at the top
4. Choose **EC2 Instance Connect**, with a Public IP, and `root` as the username
5. Click **Connect** to open a terminal session

#### Running Django Commands

Once connected to the EC2 instance, you need to access the Docker container to run Django management commands:

1. List running containers:
   ```
   $ docker ps
   ```

2. Note the container ID (first column) or name of the running elinor container

3. Execute a bash shell inside the container:
   ```
   $ docker exec -it <container_id> bash
   ```
You should be in the `/var/projects/webapp` directory inside the container, running as root.

4. Run Django management commands:
   ```
   $ python manage.py <command>
   ```

### Database Access

As with django commands, accessing the live production database should not normally be necessary; typically, to access data in the database corresponding to a deployed version of the app, you would run `python manage.py dbrestore prod` locally and then access the local copy of the database.

However: to access the RDS database (dev or prod) from your local machine using pgAdmin or psql:

#### Prerequisites

- pgAdmin or other PostgreSQL client installed locally
- IP of current development environment added to the EC2 security group
- Database credentials (available in Elastic Beanstalk environment configuration)

#### Setting Up SSH Tunnel

1. Get the EC2 instance public IP address:
   - Go to [AWS Console EC2 Instances page](https://console.aws.amazon.com/ec2/v2/home#Instances)
   - Find the elinor-dev or elinor-prod instance
   - Note the **Public IPv4 address** (e.g., `54.123.45.67`)

2. Get the RDS endpoint:
   - Go to [AWS Console RDS Databases page](https://console.aws.amazon.com/rds/home#databases)
   - Find the `socialdb` database
   - Note the **Endpoint** (e.g., `socialdb.xxxxxxxxx.us-east-1.rds.amazonaws.com`)

3. Create SSH tunnel from your local machine:

   Add an entry to your `~/.ssh/config` file (create it if it doesn't exist):

   ```
   Host elinor-dev
       HostName <ec2-public-ip>
       User ec2-user
       IdentityFile /path/to/your-key.pem
       LocalForward 5433 <rds-endpoint>:5432
   ```

   For production, create a similar entry with `elinor-prod` as the Host name.

4. Connect with the tunnel:
   ```bash
   $ ssh elinor-dev
   ```

   This establishes the SSH connection and forwards local port 5433 to the RDS database through the EC2 instance. Keep this connection open while you need database access.

#### Connecting with pgAdmin

1. Open pgAdmin
2. Right-click **Servers** → **Create** → **Server**
3. Configure connection:
   - **General tab:**
     - Name: `Elinor`
   - **Connection tab:**
     - Host: `localhost`
     - Port: `5433` (or whatever local port you used in the tunnel)
     - Maintenance database: `postgres`
     - Username: (from Elastic Beanstalk env config)
     - Password: (from Elastic Beanstalk env config)
4. Click **Save**

#### Connecting with psql

Easiest is to access the deployment container using the steps above, then run `psql` from there. But you could also run `psql` locally, with the SSH tunnel running.

#### Important Notes

- Keep the SSH tunnel running while you need database access
- Use read-only queries on production database when possible
- Always backup before making manual database changes
- Prefer using Django migrations over direct database modifications
