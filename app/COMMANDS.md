# Available Management Commands

This document lists the currently available Django management commands in the project.

## Core Commands (`apps.core`)

### `wait_for_db`

Waits for the database to be available before proceeding.

**Usage:**
```bash
docker compose run --rm app python manage.py wait_for_db
```

**Purpose:** Used in startup scripts to ensure database is ready before running migrations.

---

### `load_initial_data`

Loads initial data fixtures (cities, regions, states, municipalities, groups, permissions).

**Usage:**
```bash
# Load all fixtures
docker compose run --rm app python manage.py load_initial_data

# Skip cities data (only load auth)
docker compose run --rm app python manage.py load_initial_data --skip-cities

# Skip auth data (only load cities)
docker compose run --rm app python manage.py load_initial_data --skip-auth
```

**Purpose:** Initial data setup for new deployments or fresh databases.

**See:** [`app/fixtures/README.md`](fixtures/README.md) for detailed fixture documentation.

---

## Cities Commands (`apps.cities`)

### `fetch_mayor_data`

Fetches and updates mayor information (name, party, mandate) from Wikidata and Wikipedia.

**Usage:**
```bash
# Fetch for all municipalities
docker compose run --rm app python manage.py fetch_mayor_data

# Test with limited municipalities
docker compose run --rm app python manage.py fetch_mayor_data --limit 10

# Dry run (no database changes)
docker compose run --rm app python manage.py fetch_mayor_data --dry-run

# Skip Wikidata queries
docker compose run --rm app python manage.py fetch_mayor_data --skip-wikidata

# Skip Wikipedia scraping
docker compose run --rm app python manage.py fetch_mayor_data --skip-wikipedia
```

**Purpose:** Maintenance command to update mayor information from external sources.

**Note:** This is a data update/enrichment tool, not part of initial setup.

---

## Built-in Django Commands

The project also uses standard Django commands:

- `migrate` - Run database migrations
- `makemigrations` - Create new migrations
- `createsuperuser` - Create admin user
- `collectstatic` - Collect static files
- `shell` - Interactive Python shell
- `dbshell` - Database shell
- `dumpdata` - Export data to fixtures
- `loaddata` - Import data from fixtures

---

## Removed Commands (Now Using Fixtures)

These commands have been removed and replaced with fixture loading:

- ❌ `import_ibge_data` - Replaced by `load_initial_data` + `cities_initial_data.json`
- ❌ `import_estados_data` - Replaced by fixtures
- ❌ `import_municipios_data` - Replaced by fixtures
- ❌ `import_seaf_data` - Replaced by fixtures
- ❌ `clear_ibge_data` - Use `docker compose down -v` instead
- ❌ `create_admin_group` - Replaced by `auth_initial_data.json`
- ❌ `populate_regions` - Replaced by fixtures
- ❌ `create_region_groups` - Replaced by fixtures
- ❌ `setup_region_permissions` - Replaced by fixtures

**See:** [`app/fixtures/MIGRATION_SUMMARY.md`](fixtures/MIGRATION_SUMMARY.md) for migration details.

---

## Quick Reference

| Task | Command |
|------|---------|
| Initial setup | `python manage.py load_initial_data` |
| Update mayor data | `python manage.py fetch_mayor_data` |
| Wait for database | `python manage.py wait_for_db` |
| Dump current state | See [`scripts/dump_fixtures.sh`](../scripts/dump_fixtures.sh) |
| Run migrations | `python manage.py migrate` |
| Create admin user | `python manage.py createsuperuser` |

---

## Creating New Commands

To create a new management command:

1. Create file: `app/apps/<app>/management/commands/<command_name>.py`
2. Define `Command` class inheriting from `BaseCommand`
3. Implement `handle()` method
4. Add argument parsing with `add_arguments()` if needed
5. Document in this file

**Example structure:**
```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Description of what this command does'
    
    def add_arguments(self, parser):
        parser.add_argument('--option', type=str, help='Help text')
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Command executed'))
```

---

## Related Documentation

- [`app/fixtures/README.md`](fixtures/README.md) - Fixture documentation
- [`app/fixtures/MIGRATION_SUMMARY.md`](fixtures/MIGRATION_SUMMARY.md) - Migration from commands to fixtures
- [`DEPLOYMENT.md`](../DEPLOYMENT.md) - Deployment guide
- [`README.technical.md`](../README.technical.md) - Technical documentation

