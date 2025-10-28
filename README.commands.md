# IBGE Data Management Commands

This document describes the Django management commands available for managing Brazilian geographic data (IBGE) in the cities app.

## Overview

The cities app provides two main management commands for handling IBGE data:

- `import_ibge_data` - Import municipalities data from CSV
- `clear_ibge_data` - Clear all geographic data from database

## Import Command

### `import_ibge_data`

Imports Brazilian municipalities data from the IBGE CSV file into the database.

#### Usage

```bash
docker compose run --rm app python manage.py import_ibge_data [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--file` | string | `/data/ibge/RELATORIO_DTB_BRASIL_2024_MUNICIPIOS.csv` | Path to the CSV file |
| `--batch-size` | int | 1000 | Number of records to process in each batch |
| `--clear-existing` | flag | False | Clear existing data before importing |
| `--dry-run` | flag | False | Show what would be imported without actually importing |

#### Examples

**Basic import:**
```bash
docker compose run --rm app python manage.py import_ibge_data
```

**Dry run to preview data:**
```bash
docker compose run --rm app python manage.py import_ibge_data --dry-run
```

**Clear existing data and import:**
```bash
docker compose run --rm app python manage.py import_ibge_data --clear-existing
```

**Custom batch size for large datasets:**
```bash
docker compose run --rm app python manage.py import_ibge_data --batch-size 500
```

**Import from custom file:**
```bash
docker compose run --rm app python manage.py import_ibge_data --file /path/to/custom.csv
```

#### Data Structure

The command creates the following data hierarchy:

- **States** (27 records)
  - **Intermediate Regions** (133 records)
    - **Immediate Regions** (510 records)
      - **Municipalities** (5,571 records)

#### Performance

- **Processing time**: ~0.14 seconds for 5,571 records (dry-run)
- **Memory efficient**: Batch processing prevents memory issues
- **Database optimized**: Includes indexes for fast queries
- **Transaction safe**: Atomic operations ensure data consistency

## Clear Command

### `clear_ibge_data`

Clears all IBGE geographic data from the database.

#### Usage

```bash
docker compose run --rm app python manage.py clear_ibge_data [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--confirm` | flag | False | Confirm that you want to delete all data (required for safety) |
| `--stats-only` | flag | False | Only show current data statistics without deleting |

#### Examples

**Check current data statistics:**
```bash
docker compose run --rm app python manage.py clear_ibge_data --stats-only
```

**Clear all data (with confirmation):**
```bash
docker compose run --rm app python manage.py clear_ibge_data --confirm
```

#### Safety Features

- **Confirmation required**: `--confirm` flag prevents accidental deletion
- **Statistics preview**: `--stats-only` shows what will be deleted
- **Proper order**: Deletes in correct order respecting foreign key constraints
- **Transaction safety**: All deletions are atomic

## Development Workflow

### Initial Setup

1. **Import data for the first time:**
   ```bash
   docker compose run --rm app python manage.py import_ibge_data
   ```

2. **Verify data in Django admin:**
   - Access `/admin/` in your browser
   - Navigate to Cities section
   - Check States, Intermediate Regions, Immediate Regions, and Municipalities

### Development Cycle

1. **Clear data when needed:**
   ```bash
   docker compose run --rm app python manage.py clear_ibge_data --confirm
   ```

2. **Re-import after changes:**
   ```bash
   docker compose run --rm app python manage.py import_ibge_data
   ```

3. **Test with dry run:**
   ```bash
   docker compose run --rm app python manage.py import_ibge_data --dry-run
   ```

### Container Recreation

These commands are designed to work seamlessly with Docker container recreation:

- **Data persistence**: Commands work with mounted data volumes
- **Idempotent**: Can be run multiple times safely
- **No side effects**: Commands don't affect container state

## Error Handling

### Common Issues

1. **File not found**: Ensure CSV file exists at specified path
2. **Permission errors**: Check file permissions in container
3. **Database errors**: Ensure database is running and accessible
4. **Memory issues**: Reduce batch size for large datasets

### Troubleshooting

**Check file path:**
```bash
docker compose run --rm app ls -la /data/ibge/
```

**Verify database connection:**
```bash
docker compose run --rm app python manage.py dbshell
```

**Check command help:**
```bash
docker compose run --rm app python manage.py help import_ibge_data
docker compose run --rm app python manage.py help clear_ibge_data
```

## Data Model

The commands work with the following Django models:

- `State` - Brazilian states (UF)
- `IntermediateRegion` - Intermediate geographic regions
- `ImmediateRegion` - Immediate geographic regions  
- `Municipality` - Brazilian municipalities

All models include:
- Unique constraints on codes
- Foreign key relationships
- Database indexes for performance
- Admin interface integration

## Best Practices

1. **Always use dry-run first** for new data sources
2. **Use appropriate batch sizes** based on available memory
3. **Clear data before major imports** to avoid duplicates
4. **Monitor progress** during large imports
5. **Backup database** before clearing data in production
6. **Test commands** in development environment first

## Support

For issues or questions about these commands:

1. Check the command help: `python manage.py help <command>`
2. Review Django logs for detailed error messages
3. Verify file paths and permissions
4. Ensure database connectivity
