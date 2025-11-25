# Fixtures - Initial Data

This directory contains Django fixtures that represent the ideal database state for initial setup.

## Files

- **`cities_initial_data.json`** (~7.4MB): Geographic data including regions, states, intermediate regions, immediate regions, and municipalities with all associated metadata (mayor info, Wikipedia data, SEAF classification)
- **`auth_initial_data.json`** (~7.6KB): Authentication and authorization data including groups, resource permissions, and group-permission assignments

## Loading Fixtures

### Automatic Loading

Fixtures are automatically loaded on first startup when the database is empty:

```bash
docker compose up
```

The `run.sh` script checks if data exists and loads fixtures if needed.

### Manual Loading

To manually load all fixtures:

```bash
docker compose run --rm app python manage.py load_initial_data
```

To load specific fixtures:

```bash
# Only cities data
docker compose run --rm app python manage.py load_initial_data --skip-auth

# Only auth data
docker compose run --rm app python manage.py load_initial_data --skip-cities
```

Or use Django's built-in loaddata:

```bash
docker compose run --rm app python manage.py loaddata cities_initial_data.json
docker compose run --rm app python manage.py loaddata auth_initial_data.json
```

## Updating Fixtures

When the database state has been updated and needs to be captured as the new ideal state:

### 1. Dump Cities Data

```bash
docker compose run --rm app python manage.py dumpdata \
  cities.Region \
  cities.State \
  cities.IntermediateRegion \
  cities.ImmediateRegion \
  cities.Municipality \
  --indent 2 \
  --output /app/fixtures/cities_initial_data.json
```

### 2. Dump Auth Data

```bash
docker compose run --rm app python manage.py dumpdata \
  auth.Group \
  custom_auth.ResourcePermission \
  custom_auth.GroupResourcePermission \
  --indent 2 \
  --output /app/fixtures/auth_initial_data.json
```

### Convenience Script

A script is provided to dump all fixtures at once:

```bash
docker compose run --rm app sh -c "python manage.py dumpdata cities.Region cities.State cities.IntermediateRegion cities.ImmediateRegion cities.Municipality --indent 2 --output /app/fixtures/cities_initial_data.json && python manage.py dumpdata auth.Group custom_auth.ResourcePermission custom_auth.GroupResourcePermission --indent 2 --output /app/fixtures/auth_initial_data.json"
```

## What's NOT Included

Fixtures explicitly exclude:

- **User accounts** (`User`, `UserPermission`): User-specific, not initial data
- **Logs** (`MunicipalityLog`, `PermissionLog`): Audit trails, not initial data
- **Django's Permission model**: Auto-generated from models, managed by Django

## Architecture

### Why Split by App?

1. **Modularity**: Update cities or auth data independently
2. **Maintainability**: Smaller files, easier to review
3. **Git-friendly**: Better diff/merge handling
4. **Selective loading**: Load only what's needed for testing

### Load Order

Fixtures are loaded in dependency order:

1. **Cities**: Has internal FK dependencies (Region → State → IntermediateRegion → ImmediateRegion → Municipality)
2. **Auth**: Depends on cities.Region (GroupResourcePermission has optional FK to Region)

### Alternative Approach: Management Commands

The previous approach used management commands:

- ❌ `import_ibge_data`
- ❌ `import_estados_data`
- ❌ `import_municipios_data`
- ❌ `import_seaf_data`
- ❌ `import_wiki_data`

**Migration Rationale:**

- Fixtures are Django's standard for initial data
- Single source of truth (current DB state)
- Simpler deployment process
- No dependency on external CSV/JSON files in `/data` directory
- Easier to version control database state

## Troubleshooting

### Fixture Load Fails

If fixture loading fails due to constraint violations:

1. Check load order (cities must load before auth)
2. Ensure database is empty or use `--ignorenonexistent`
3. Check for manual edits to fixture files

```bash
# Clear database and reload
docker compose down -v
docker compose up
```

### Update Fixture After Manual Changes

If you've made manual changes via Django admin:

```bash
# Dump current state
docker compose run --rm app python manage.py dumpdata cities.Region cities.State cities.IntermediateRegion cities.ImmediateRegion cities.Municipality --indent 2 --output /app/fixtures/cities_initial_data.json

# Commit to version control
git add app/fixtures/cities_initial_data.json
git commit -m "Update cities fixture with manual changes"
```

### Large Fixture File

The `cities_initial_data.json` file is ~7.4MB due to 5,570 municipalities. Alternatives:

1. **Keep as-is** (recommended): Complete, accurate initial state
2. **Compress**: Store as `.json.gz` (requires custom loader)
3. **Split by state**: 27 separate fixtures (increases complexity)
4. **Minimal set**: Only major cities (incomplete data)

**Recommendation**: Keep complete fixture for production-accurate testing.

## Migration from Management Commands

Old workflow:
```bash
python manage.py migrate
python manage.py import_ibge_data
python manage.py import_estados_data
python manage.py import_municipios_data
python manage.py import_seaf_data
python manage.py import_wiki_data
```

New workflow:
```bash
python manage.py migrate
python manage.py load_initial_data
```

**Benefits:**
- 5 commands → 1 command
- No external data dependencies
- Faster loading (no parsing/processing)
- Idempotent (can run multiple times safely)

