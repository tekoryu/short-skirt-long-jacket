#!/bin/sh

set -e

python manage.py wait_for_db
python manage.py collectstatic --noinput
python manage.py migrate

if [ "$DEBUG" = "True" ]; then
    echo "Starting development server..."
    python manage.py runserver 0.0.0.0:8000
else
    echo "Starting production server with Gunicorn..."
    gunicorn --bind 0.0.0.0:8000 config.wsgi:application
fi 
