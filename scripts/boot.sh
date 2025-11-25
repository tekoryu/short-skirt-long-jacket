#!/bin/bash

# Parse command line arguments
SKIP_BUILD=false
for arg in "$@"; do
    case $arg in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        *)
            ;;
    esac
done

healthCheckUrl="http://localhost:8000/health/"
timeoutSeconds=120
pollIntervalSeconds=30

if [ "$SKIP_BUILD" = false ]; then
    echo "Tearing down existing services and cleaning up project resources..."
    docker compose down -v --remove-orphans --rmi all

    echo "Building and starting services with 'docker compose up'..."
    docker compose up --build -d

    startTime=$(date +%s)
    serviceReady=false

    echo "Waiting for the service to become healthy at '$healthCheckUrl'..."

    while true; do
        currentTime=$(date +%s)
        elapsedSeconds=$((currentTime - startTime))

        if [ $elapsedSeconds -ge $timeoutSeconds ]; then
            break
        fi

        statusCode=$(curl -s -o /dev/null -w "%{http_code}" "$healthCheckUrl" 2>/dev/null)

        if [ "$statusCode" = "200" ]; then
            echo "✅ Service is healthy after ${elapsedSeconds} seconds. Proceeding..."
            serviceReady=true
            break
        else
            echo "Service responded with status $statusCode after ${elapsedSeconds}s. Retrying in ${pollIntervalSeconds}s..."
        fi

        sleep $pollIntervalSeconds
    done

    if [ "$serviceReady" = false ]; then
        echo "❌ Error: Service did not become healthy within the $timeoutSeconds-second timeout."
        echo "Check the container logs for errors: docker compose logs app"
        exit 1
    fi
else
    echo "⏩ Skipping build step (--skip-build flag detected)..."
    echo "Assuming services are already running."
fi

echo "Running post-startup commands..."
docker compose run --rm app sh -c "python manage.py createsuperuser --noinput"

echo "Running migrations..."
docker compose run --rm app sh -c "python manage.py migrate"

echo "Collecting static files..."
docker compose run --rm app sh -c "python manage.py collectstatic --noinput"

echo "Importing IBGE data..."
docker compose run --rm app sh -c "python manage.py import_ibge_data"

echo "Enriching states metadata..."
docker compose run --rm app sh -c "python manage.py import_estados_data"

echo "Updating municipalities metadata..."
docker compose run --rm app sh -c "python manage.py import_municipios_data"

echo "Applying SEAF classification data..."
docker compose run --rm app sh -c "python manage.py import_seaf_data"

echo "Loading Wikipedia infobox data..."
docker compose run --rm app sh -c "python manage.py import_wiki_data"

echo "Finished booting up the application."

echo "Opening application in browser."
xdg-open "http://localhost:8000" 2>/dev/null || open "http://localhost:8000" 2>/dev/null || echo "Please open http://localhost:8000 in your browser"
