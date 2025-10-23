$healthCheckUrl = "http://localhost:8000/health"
$timeoutSeconds = 120
$pollIntervalSeconds = 30


Write-Host "Tearing down existing services and cleaning up project resources..."
docker compose down -v --remove-orphans --rmi all

Write-Host "Building and starting services with 'docker compose up'..."
docker compose up --build -d # The -d flag is crucial to run in the background

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$serviceReady = $false

while ($stopwatch.Elapsed.TotalSeconds -lt $timeoutSeconds) {
    Write-Host "Waiting for the service to become healthy at '$healthCheckUrl'..."
    Start-Sleep -Seconds $pollIntervalSeconds
    try {
        $response = Invoke-WebRequest -Uri $healthCheckUrl -UseBasicParsing -ErrorAction Stop
        
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Service is healthy. Proceeding..."
            $serviceReady = $true
            break
        } else {
            Write-Host "Service responded with status $($response.StatusCode). Retrying..."
        }
    }
    catch {
        Write-Host "Waiting for service to respond... Retrying in $pollIntervalSeconds seconds."
    }
}

$stopwatch.Stop()

if ($serviceReady) {
    Write-Host "Running post-startup commands..."
    docker compose run --rm app sh -c "python manage.py createsuperuser --noinput"
    
    Write-Host "Opening application in browser."
    Start-Process "http://localhost:8000"
} else {
    Write-Host "❌ Error: Service did not become healthy within the $timeoutSeconds-second timeout."
    Write-Host "Check the container logs for errors: docker compose logs app"
    exit 1
}

Write-Host "Finished booting up the application."