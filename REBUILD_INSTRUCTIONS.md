# Rebuild Instructions After Security Fixes

## Quick Start

If you just want to rebuild and test immediately:

```bash
# 1. Stop existing containers
docker compose down -v

# 2. Rebuild with new changes
docker compose build --no-cache

# 3. Start containers
docker compose up -d

# 4. Check logs
docker compose logs -f app
```

## Detailed Setup for Development with Proxy

If you need to use the proxy during development:

### 1. Update your .env file

Copy from .env.example if you don't have a .env file:
```bash
cp .env.example .env
```

Then edit `.env` and set:
```env
DEBUG=True
USE_PROXY=true
HTTP_PROXY_URL=http://10.1.101.101:8080
```

### 2. Rebuild and start
```bash
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

## Setup for Production (or Development without Proxy)

### 1. Update your .env file
```env
DEBUG=False
USE_PROXY=false

# Generate a new SECRET_KEY (NEVER use the example one in production!)
SECRET_KEY=<your-generated-secret-key>

# Set your domain
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Use strong database password
DB_PASSWORD=<strong-password-here>
```

Generate a new SECRET_KEY:
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 2. Rebuild and start
```bash
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

## Verify Everything Works

### 1. Check containers are running
```bash
docker compose ps
```

You should see both `db` and `app` services running and healthy.

### 2. Check application logs
```bash
docker compose logs -f app
```

Look for:
- `Starting production server with Gunicorn...` (if DEBUG=False)
- `Starting development server...` (if DEBUG=True)
- No error messages

### 3. Check the application is responding
```bash
curl http://localhost:8000/health/
```

Should return: `{"status":"ok"}`

### 4. Check security logs are being created
```bash
docker compose exec app ls -la /vol/web/logs/
```

Should show:
- `django.log`
- `security.log`

### 5. Test rate limiting on login

Try to login 6 times with wrong password:
```bash
# This should eventually return a 429 or rate limit error
for i in {1..6}; do
  curl -X POST http://localhost:8000/auth/login/ \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "email=test@example.com&password=wrongpassword"
  echo "\nAttempt $i"
  sleep 1
done
```

After 5 failed attempts, you should be rate-limited.

## Database Access

If you need to access the database from your host machine, uncomment these lines in `compose.yaml`:

```yaml
  db:
    # ... other config ...
    ports:
      - "5432:5432"
```

Then restart:
```bash
docker compose down
docker compose up -d
```

⚠️ **Warning:** Only do this in development. Never expose database ports in production.

## Running Migrations

If you need to run migrations:
```bash
docker compose exec app python manage.py migrate
```

## Creating a Superuser

```bash
docker compose exec app python manage.py createsuperuser
```

## Importing IBGE Data

```bash
docker compose exec app python manage.py import_ibge_data
```

## Collecting Static Files

Static files are collected automatically on startup, but if you need to run manually:
```bash
docker compose exec app python manage.py collectstatic --noinput
```

## Viewing Logs

### Application logs (console)
```bash
docker compose logs -f app
```

### Django file logs
```bash
docker compose exec app tail -f /vol/web/logs/django.log
```

### Security logs
```bash
docker compose exec app tail -f /vol/web/logs/security.log
```

### Database logs
```bash
docker compose logs -f db
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker compose logs app

# Try rebuilding without cache
docker compose build --no-cache app
docker compose up -d
```

### Can't connect to database
```bash
# Check database is healthy
docker compose ps

# Check database logs
docker compose logs db

# Try restarting database
docker compose restart db
```

### Permission errors in logs
```bash
# Fix volume permissions
docker compose down
docker volume rm short-skirt-long-jacket_static_volume
docker volume rm short-skirt-long-jacket_media_volume
docker compose up -d
```

### Rate limiting not working
```bash
# Check django-ratelimit is installed
docker compose exec app pip list | grep ratelimit

# If not, rebuild
docker compose build --no-cache app
docker compose up -d
```

### Proxy errors during build
```bash
# If you need proxy for apt/apk but not pip
# Edit Dockerfile and adjust proxy settings

# Or if proxy is causing issues, disable it
# In .env:
USE_PROXY=false
```

## Testing the New Features

### 1. Test Security Headers (Production mode)

Set `DEBUG=False` in `.env`, restart, then:

```bash
curl -I http://localhost:8000/
```

Look for headers like:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`

### 2. Test Rate Limiting

**Login rate limit (5 per 5 minutes):**
```bash
# Fail 6 times
for i in {1..6}; do
  curl -X POST http://localhost:8000/auth/login/ \
    -d "email=test@test.com&password=wrong" \
    -b cookies.txt -c cookies.txt
done
```

**Registration rate limit (3 per hour):**
```bash
# Try 4 registrations
for i in {1..4}; do
  curl -X POST http://localhost:8000/auth/register/ \
    -d "email=test$i@test.com&password=test123&username=test$i"
done
```

### 3. Test Permission Logging

1. Login to admin: http://localhost:8000/admin/
2. Try to access a restricted resource
3. Check the PermissionLog model - should only see denials
4. Check application logs - successful access in DEBUG logs

```bash
docker compose exec app python manage.py shell
```

```python
from apps.auth.models import PermissionLog
# Should only see 'access_denied' actions for permission checks
PermissionLog.objects.filter(action='access_denied').count()
```

### 4. Test Municipality Views

```bash
# This should work and return proper JSON with state names
curl http://localhost:8000/cities/api/
```

Should return city data with proper state names from the related model.

## Clean Reset

If you want to completely reset everything:

```bash
# Stop and remove everything
docker compose down -v

# Remove all images
docker compose rm -f
docker rmi $(docker images 'short-skirt-long-jacket*' -q)

# Remove all volumes
docker volume prune -f

# Rebuild from scratch
docker compose build --no-cache
docker compose up -d

# Recreate database
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser
docker compose exec app python manage.py import_ibge_data
```

## Performance Tuning

### Adjust Gunicorn Workers

In `scripts/run.sh`, adjust based on your server:

```bash
# Formula: (2 x CPU cores) + 1
# For 2 CPU cores:
--workers 5

# For 4 CPU cores:
--workers 9
```

### Adjust Rate Limits

In `app/apps/auth/views.py`:

```python
# More restrictive login
@ratelimit(key='ip', rate='3/5m', method='POST', block=True)

# Less restrictive login
@ratelimit(key='ip', rate='10/5m', method='POST', block=True)
```

### Adjust Database Connection Pool

In `app/config/settings.py`:

```python
# Longer connection pooling (30 minutes)
CONN_MAX_AGE = 1800

# Shorter for more frequent connections
CONN_MAX_AGE = 300
```

## Next Steps

1. ✅ Rebuild your containers with the new changes
2. ✅ Test rate limiting works
3. ✅ Verify security headers in production mode
4. ✅ Check logs are being written properly
5. ⚠️ **IMPORTANT**: Remove .env from git (see SECURITY_FIXES.md)
6. ⚠️ Rotate all secrets if .env was ever committed
7. 📝 Write tests for authentication and permissions
8. 🔒 Set up SSL/TLS for production
9. 📊 Set up monitoring and alerting
10. 🔐 Consider implementing email verification

---

**Need help?** Check the logs and consult SECURITY_FIXES.md for detailed information about each change.
