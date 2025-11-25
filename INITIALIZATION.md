# Application Initialization Guide

This document explains how the application initializes and loads data automatically.

## TL;DR

**Just run:**
```bash
./scripts/boot.sh
```

Everything else happens automatically. No manual data loading needed.

---

## How It Works

### Automatic Initialization Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. YOU START CONTAINERS                                     │
│    $ ./scripts/boot.sh                                      │
│    OR                                                        │
│    $ docker compose up                                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CONTAINER STARTS → AUTOMATIC ENTRYPOINT                  │
│    Docker runs: /scripts/run.sh                             │
│                                                              │
│    ✓ Wait for database                                      │
│    ✓ Collect static files                                   │
│    ✓ Run migrations                                         │
│    ✓ Check if database is empty                             │
│       └─► If empty: Load fixtures automatically             │
│    ✓ Create superuser (if configured)                       │
│    ✓ Start server (runserver or gunicorn)                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. APPLICATION READY                                        │
│    http://localhost:8000                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Scripts Explained

### `/scripts/run.sh` - Automatic Entrypoint

**Purpose:** Container initialization script  
**Called by:** Docker automatically (defined in Dockerfile CMD)  
**When:** Every time the container starts  
**Where:** Inside the container  
**You call it:** Never (it's automatic)

**What it does:**
1. Waits for database to be ready
2. Collects static files
3. Applies database migrations
4. Checks if database is empty (Region.objects.count() == 0)
5. If empty → Loads `cities_initial_data.json` and `auth_initial_data.json`
6. Creates superuser if environment variables are set
7. Starts development server (DEBUG=True) or Gunicorn (production)

**Key Feature:** Idempotent - safe to run multiple times. Only loads data if database is empty.

---

### `/scripts/boot.sh` - Development Convenience Script

**Purpose:** Orchestration script for local development  
**Called by:** You, manually  
**When:** When you want a clean build from scratch  
**Where:** On your host machine  

**What it does:**
1. Tears down existing containers and volumes (`docker compose down -v`)
2. Builds and starts containers (`docker compose up --build -d`)
   - This triggers `run.sh` automatically (see above)
3. Waits for application health check to pass
4. Opens browser automatically
5. Shows useful commands and documentation links

**What it DOESN'T do:**
- ❌ Run migrations manually (run.sh does this)
- ❌ Load fixtures manually (run.sh does this)
- ❌ Create superuser manually (run.sh does this)

---

## Usage Examples

### First Time Setup

```bash
# Clone repository
git clone <repo-url>
cd short-skirt-long-jacket

# Copy environment file
cp .env.example .env

# Edit .env with your settings
nano .env

# Start everything (automatic initialization)
./scripts/boot.sh
```

**What happens:**
- Containers build
- Database starts
- `run.sh` detects empty database
- Fixtures load automatically (5,570 municipalities, regions, states, groups, permissions)
- Superuser created
- Browser opens to http://localhost:8000

**Time:** ~60 seconds (first time with data loading)

---

### Subsequent Starts

```bash
# If containers are stopped
docker compose up

# OR for clean rebuild
./scripts/boot.sh
```

**What happens:**
- Containers start
- `run.sh` detects data exists
- Skips fixture loading
- Server starts

**Time:** ~10 seconds (no data loading needed)

---

### Clean Slate (Reset Everything)

```bash
./scripts/boot.sh
```

**What happens:**
- `docker compose down -v` removes all volumes (database wiped)
- Fresh build
- `run.sh` detects empty database
- Fixtures reload automatically

**Time:** ~90 seconds (rebuild + data loading)

---

## Initial Data (Fixtures)

### What Gets Loaded Automatically

**Cities Data** (`app/fixtures/cities_initial_data.json` - 7.4MB):
- 5 Regions (Norte, Nordeste, Centro-Oeste, Sudeste, Sul)
- 27 States
- 133 Intermediate Regions
- 510 Immediate Regions
- 5,570 Municipalities (with mayor data, Wikipedia data, SEAF classification)

**Auth Data** (`app/fixtures/auth_initial_data.json` - 7.6KB):
- Groups (Admin, Regional Admin, etc.)
- Resource Permissions (view, add, change, delete)
- Group-Permission Assignments (regional scoping)

### What Does NOT Get Loaded

- ❌ User accounts (except superuser from .env)
- ❌ Log entries (MunicipalityLog, PermissionLog)
- ❌ Session data
- ❌ Temporary data

---

## Environment Variables for Initialization

Set these in `.env` file:

```bash
# Database (required)
DB_NAME=seaf_db
DB_USER=seaf_user
DB_PASSWORD=your_secure_password

# Superuser (automatic creation)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=your_admin_password

# Debug mode (affects which server starts)
DEBUG=True
```

If superuser variables are set, `run.sh` automatically creates the admin user on first start.

---

## Troubleshooting

### Data Not Loading

**Check logs:**
```bash
docker compose logs app
```

**Look for:**
```
Database is empty. Loading initial data...
✓ Initial data loaded successfully
```

**If not present:**
1. Check fixtures exist: `ls -lh app/fixtures/*.json`
2. Check database is empty: `docker compose exec app python manage.py shell -c "from apps.cities.models import Region; print(Region.objects.count())"`
3. Manually load: `docker compose exec app python manage.py load_initial_data`

---

### Container Starts But No Data

**Possible causes:**
1. Database volume persisted from previous run (has old data)
2. Fixtures missing or corrupt

**Solution:**
```bash
# Full reset
docker compose down -v
./scripts/boot.sh
```

---

### Superuser Not Created

**Check:**
1. Environment variables set in `.env`
2. Logs show: `docker compose logs app | grep -i superuser`

**Manual creation:**
```bash
docker compose exec app python manage.py createsuperuser
```

---

### "Database is already populated" But Data Is Wrong

The check only looks at `Region` table. If you manually deleted data but left some regions, it won't reload.

**Solution:**
```bash
# Force reload
docker compose down -v          # Wipe everything
./scripts/boot.sh              # Fresh start

# OR manually
docker compose exec app python manage.py load_initial_data
```

---

## Production Deployment

In production, `run.sh` works the same way:

```bash
# On production server
cd /opt/seaf
./deploy.sh
```

**First deployment:**
- Empty database → Fixtures load automatically
- Creates superuser from environment variables
- Starts Gunicorn (production server)

**Subsequent deployments:**
- Data exists → Skips fixture loading
- Runs migrations (if any)
- Restarts server

---

## Updating Fixtures

If you've made changes to the database and want to capture the new state:

```bash
# Dump current database to fixtures
./scripts/dump_fixtures.sh

# Commit changes
git add app/fixtures/*.json
git commit -m "Update fixtures with new data"

# Deploy
git push
```

See [`app/fixtures/README.md`](app/fixtures/README.md) for detailed fixture management.

---

## Architecture Decision

**Why automatic initialization in entrypoint?**

✅ **Pros:**
- Zero manual steps
- Works everywhere (dev, staging, production)
- Idempotent (safe to restart containers)
- Standard Docker pattern
- No separate init container needed

❌ **Cons:**
- Small overhead on every container start (mitigated by empty-check)
- Can cause issues with multiple replicas (but we check before loading)

**Alternative approaches considered:**
- Init container pattern (overkill for single-replica deployment)
- Django data migrations (too slow for 7.4MB fixtures)
- Manual loading (error-prone, requires documentation)

**Decision:** Automatic entrypoint initialization is the best balance of simplicity and reliability for this project.

---

## Related Documentation

- [`app/fixtures/README.md`](app/fixtures/README.md) - Fixture management
- [`app/fixtures/MIGRATION_SUMMARY.md`](app/fixtures/MIGRATION_SUMMARY.md) - Migration from management commands
- [`app/COMMANDS.md`](app/COMMANDS.md) - Available management commands
- [`DEPLOYMENT.md`](DEPLOYMENT.md) - Production deployment guide
- [`README.technical.md`](README.technical.md) - Technical architecture

---

## Quick Reference

| Task | Command |
|------|---------|
| First time setup | `./scripts/boot.sh` |
| Start containers | `docker compose up` |
| Clean rebuild | `./scripts/boot.sh` |
| View logs | `docker compose logs -f app` |
| Stop everything | `docker compose down` |
| Reset database | `docker compose down -v && ./scripts/boot.sh` |
| Manual fixture load | `docker compose exec app python manage.py load_initial_data` |
| Update fixtures | `./scripts/dump_fixtures.sh` |

---

**Remember:** You never need to manually load data. It happens automatically via `run.sh` every time containers start.

