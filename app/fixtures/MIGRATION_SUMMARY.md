# Migration Summary: Management Commands → Fixtures

## Overview

The project has been migrated from using custom management commands for data initialization to Django's built-in fixture system.

## What Changed

### Before (Management Commands)

```bash
python manage.py migrate
python manage.py import_ibge_data
python manage.py import_estados_data
python manage.py import_municipios_data
python manage.py import_seaf_data
python manage.py import_wiki_data
python manage.py create_admin_group
python manage.py populate_regions
python manage.py create_region_groups
python manage.py setup_region_permissions
```

**Issues:**
- 9 separate commands to run
- Dependent on external CSV/JSON files in `/data` directory
- Order-dependent execution
- Slower (parsing + processing overhead)
- Harder to version control exact database state

### After (Fixtures)

```bash
python manage.py migrate
python manage.py load_initial_data
```

**Benefits:**
- 2 commands total (migrate + load_initial_data)
- Self-contained (fixtures include all data)
- Automatic on first startup
- Faster (direct database import)
- Version controlled exact database state

## Files

### New Files

1. **`app/fixtures/cities_initial_data.json`** (7.4MB)
   - All regions, states, intermediate regions, immediate regions, municipalities
   - Includes SEAF classifications, Wikipedia data, mayor information

2. **`app/fixtures/auth_initial_data.json`** (7.6KB)
   - Groups, resource permissions, group-permission assignments

3. **`app/apps/core/management/commands/load_initial_data.py`**
   - New management command to load fixtures in correct order
   - Supports `--skip-cities` and `--skip-auth` flags

4. **`app/fixtures/README.md`**
   - Complete documentation on fixture usage
   - Instructions for updating fixtures
   - Troubleshooting guide

5. **`scripts/dump_fixtures.sh`**
   - Helper script to dump current database state to fixtures
   - Convenient for capturing database changes

### Modified Files

1. **`scripts/run.sh`**
   - Added automatic fixture loading on first startup
   - Checks if database is empty before loading
   - Creates superuser automatically

2. **`scripts/boot.sh`**
   - **[REMOVED]** No longer needed - all functionality handled by docker compose + run.sh
   - Initialization now uses standard docker compose commands

3. **`DEPLOYMENT.md`**
   - Updated deployment instructions
   - Added fixture management section

4. **`README.technical.md`**
   - Updated to reflect fixture-based approach
   - Removed references to deprecated commands

5. **`README.commands.md`**
   - Removed (deprecated commands documentation no longer needed)

## Migration Process

The migration was done as follows:

1. **Captured current database state** (the "ideal state"):
   ```bash
   docker compose run --rm app python manage.py dumpdata cities.Region ... --output fixtures/cities_initial_data.json
   docker compose run --rm app python manage.py dumpdata auth.Group ... --output fixtures/auth_initial_data.json
   ```

2. **Created loading command** (`load_initial_data`):
   - Loads fixtures in correct order (cities first, then auth)
   - Optional flags to skip certain fixtures

3. **Updated deployment scripts**:
   - `run.sh` now loads fixtures automatically on empty database
   - `boot.sh` removed (replaced by standard docker compose commands)

4. **Updated documentation**:
   - Marked old commands as deprecated
   - Created comprehensive fixture documentation

## Backward Compatibility

### Deprecated Commands (Still Available)

These commands still exist but are no longer used:

- `import_ibge_data`
- `import_estados_data`
- `import_municipios_data`
- `import_seaf_data`
- `import_wiki_data` (if it existed)
- `create_admin_group`
- `populate_regions`
- `create_region_groups`
- `setup_region_permissions`

**Status**: Available but not called. Can be removed in future cleanup.

### New Workflow

**Development:**
```bash
docker compose up  # Fixtures load automatically on first run
```

**Production:**
```bash
./deploy.sh  # Fixtures load automatically on first deployment
```

**Manual fixture loading:**
```bash
docker compose run --rm app python manage.py load_initial_data
```

**Updating fixtures (after making database changes):**
```bash
./scripts/dump_fixtures.sh
git add app/fixtures/*.json
git commit -m "Update fixtures"
```

## Benefits Realized

1. **Simplicity**: 9 commands → 1 command
2. **Speed**: Faster loading (no CSV parsing)
3. **Reliability**: Exact database state reproduction
4. **Maintainability**: Single source of truth
5. **Version Control**: Database state in git
6. **Automation**: Loads automatically on first run

## Rollback Plan

If issues arise, rollback is simple:

1. Revert changes to `scripts/run.sh`
2. Re-enable old commands in deployment workflow
3. Delete fixture files

The old management commands are still present and functional.

## Future Considerations

### Optional Cleanup (Later)

1. **Remove deprecated commands**: Delete unused management command files
2. **Remove external data files**: Delete `/data/ibge`, `/data/repo`, `/data/SEAF` if no longer needed
3. **Compress fixtures**: Consider gzip compression if file size becomes an issue

### Fixture Updates

When database schema or data changes:

1. Make changes via Django admin or migrations
2. Run `./scripts/dump_fixtures.sh`
3. Review and commit fixture changes
4. Deploy as usual

## Testing

To test the new fixture-based approach:

```bash
# Clean slate
docker compose down -v

# Start fresh (should load fixtures automatically)
docker compose up

# Verify data loaded
docker compose run --rm app python manage.py shell -c "from apps.cities.models import Region, Municipality; print(f'Regions: {Region.objects.count()}, Municipalities: {Municipality.objects.count()}')"
```

Expected output:
```
Regions: 5, Municipalities: 5570
```

## Questions?

See:
- [`app/fixtures/README.md`](README.md) - Fixture documentation
- [`DEPLOYMENT.md`](../../DEPLOYMENT.md) - Deployment guide
- [`README.technical.md`](../../README.technical.md) - Technical documentation

