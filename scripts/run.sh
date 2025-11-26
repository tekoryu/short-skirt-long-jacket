#!/bin/sh
#
# Container Entrypoint Script
# ===========================
# This script runs AUTOMATICALLY when the container starts.
# It handles all initialization: migrations, fixtures, static files, superuser.
#
# Called by: Docker (defined as CMD in Dockerfile)
# When: Every time the container starts
# Where: Inside the container
#
# You don't need to call this manually!
#

set -e

echo "🚀 Starting application initialization..."

python manage.py wait_for_db
echo "✓ Database connection established"

python manage.py collectstatic --noinput
echo "✓ Static files collected"

python manage.py migrate
echo "✓ Database migrations applied"

# Load initial data if database is empty
# Check if Region table has data
echo "Checking if initial data needs to be loaded..."
REGION_COUNT=$(python manage.py shell -c "from apps.cities.models import Region; print(Region.objects.count())" 2>&1)

# Trim whitespace and check if it's a valid number
REGION_COUNT=$(echo "$REGION_COUNT" | tr -d '[:space:]')

# If REGION_COUNT is not a number or is 0, load data
if ! [[ "$REGION_COUNT" =~ ^[0-9]+$ ]] || [ "$REGION_COUNT" = "0" ]; then
    echo "📦 Database is empty or check failed. Loading initial data..."
    python manage.py load_initial_data
    echo "✓ Initial data loaded successfully"
else
    echo "✓ Database already contains $REGION_COUNT regions. Skipping initial data load."
fi

# Create superuser if it doesn't exist (using environment variables)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --noinput 2>/dev/null && echo "✓ Superuser created" || echo "✓ Superuser already exists"
fi

echo "✅ Initialization complete"
echo ""

if [ "$DEBUG" = "True" ]; then
    echo "Starting development server..."
    python manage.py runserver 0.0.0.0:8000
else
    echo "Starting production server with Gunicorn..."
    gunicorn --bind 0.0.0.0:8000 \
        --workers $(($(nproc) + 1)) \
        --timeout 60 \
        --worker-class sync \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --access-logfile - \
        --error-logfile - \
        --log-level info \
        config.wsgi:application
fi 
