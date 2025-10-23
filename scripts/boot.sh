#!/bin/bash

healthCheckUrl="http://localhost:8000/health"
timeoutSeconds=120
pollIntervalSeconds=30

echo "Tearing down existing services and cleaning up project resources..."
docker compose down -v --remove-orphans --rmi all

echo "Building and starting services with 'docker compose up'..."
docker compose up --build -d

startTime=$(date +%s)
serviceReady=false

while true; do
    currentTime=$(date +%s)
    elapsedSeconds=$((currentTime - startTime))
    
    if [ $elapsedSeconds -ge $timeoutSeconds ]; then
        break
    fi
    
    echo "Waiting for the service to become healthy at '$healthCheckUrl'..."
    sleep $pollIntervalSeconds
    
    statusCode=$(curl -s -o /dev/null -w "%{http_code}" "$healthCheckUrl" 2>/dev/null)
    
    if [ "$statusCode" = "200" ]; then
        echo "✅ Service is healthy. Proceeding..."
        serviceReady=true
        break
    else
        echo "Service responded with status $statusCode. Retrying..."
    fi
done

if [ "$serviceReady" = true ]; then
    echo "Running post-startup commands..."
    docker compose run --rm app sh -c "python manage.py createsuperuser --noinput"
    
    echo "Opening application in browser."
    xdg-open "http://localhost:8000" 2>/dev/null || open "http://localhost:8000" 2>/dev/null || echo "Please open http://localhost:8000 in your browser"
else
    echo "❌ Error: Service did not become healthy within the $timeoutSeconds-second timeout."
    echo "Check the container logs for errors: docker compose logs app"
    exit 1
fi

echo "Finished booting up the application."

