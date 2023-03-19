#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# init migrations
python manage.py makemigrations
python manage.py makemigrations sheets_to_web
python manage.py makemigrations django_celery_beat
python manage.py migrate


exec "$@"