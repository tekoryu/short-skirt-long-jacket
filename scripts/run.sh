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
    gunicorn --bind 0.0.0.0:8000 \
        --workers 4 \
        --timeout 60 \
        --worker-class sync \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --access-logfile - \
        --error-logfile - \
        --log-level info \
        config.wsgi:application
fi 
