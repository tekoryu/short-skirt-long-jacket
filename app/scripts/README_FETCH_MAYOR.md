# Mayor Data Fetcher Script

## Overview

`fetch_mayor_data_from_json.py` is a standalone Python script that reads `municipios.json`, fetches mayor data from Wikidata and Wikipedia, and outputs an enriched CSV file.

## Key Differences from Django Command

- **Standalone**: No Django dependencies, runs as pure Python script
- **Input**: Reads from JSON files (not database)
- **Output**: Creates CSV with all original + new fields
- **One-time use**: Designed for data enrichment, not recurring updates

## Usage

### Option 1: Run Inside Docker (Recommended)

The script is in the `/app/scripts/` directory (WORKDIR), so it works without rebuilding:

```bash
# Test with 1 municipality
docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --limit 1

# Process all municipalities
docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --output municipios_enriched.csv

# Skip Wikidata (Wikipedia only)
docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --skip-wikidata --output output.csv

# Test with 10 municipalities
docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --limit 10 --output test.csv

# Export to JSON format
docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --format json --output municipios_enriched.json
```

### Option 2: Run Outside Docker

Install dependencies first:

```bash
pip install requests beautifulsoup4 SPARQLWrapper
```

Then run:

```bash
cd /home/tekoryu/dev/short-skirt-long-jacket/app

# Test with 1 municipality (requires custom paths for local)
python scripts/fetch_mayor_data_from_json.py --limit 1 \
    --municipios ../data/municipios-brasileiros/json/municipios.json \
    --estados ../data/municipios-brasileiros/json/estados.json

# Process all municipalities
python scripts/fetch_mayor_data_from_json.py \
    --municipios ../data/municipios-brasileiros/json/municipios.json \
    --estados ../data/municipios-brasileiros/json/estados.json \
    --output municipios_enriched.csv

# Export to JSON format
python scripts/fetch_mayor_data_from_json.py \
    --municipios ../data/municipios-brasileiros/json/municipios.json \
    --estados ../data/municipios-brasileiros/json/estados.json \
    --format json --output municipios_enriched.json
```

## Command Line Arguments

- `--municipios PATH`: Path to municipios.json (default: `/data/municipios-brasileiros/json/municipios.json` for Docker)
- `--estados PATH`: Path to estados.json (default: `/data/municipios-brasileiros/json/estados.json` for Docker)
- `--output PATH`: Output file path (default: `municipios_enriched.csv`)
- `--format {csv,json}`: Output format - csv or json (default: `csv`)
- `--limit N`: Process only N municipalities (for testing)
- `--skip-wikidata`: Skip Wikidata queries (use Wikipedia only)
- `--skip-wikipedia`: Skip Wikipedia scraping (use Wikidata only)

**Note**: Default paths work for Docker. For local execution, provide custom paths with `--municipios` and `--estados`.

## Output Structure

The output (CSV or JSON) contains all original fields from `municipios.json` plus:

- `mayor_name`: Name of the current mayor
- `mayor_party`: Political party (e.g., PT, PSDB)
- `mayor_mandate_start`: Start year of mandate
- `mayor_mandate_end`: End year of mandate
- `wikipedia_url`: URL of Wikipedia page (if used)
- `data_source`: Source of data (wikidata/wikipedia/none)

**Format Differences:**
- **CSV**: Compatible with spreadsheets, databases. Some fields may be empty strings.
- **JSON**: Preserves data types (integers, nulls). Better for programmatic use.

## Adding New Fields

### From Wikidata

1. **Find the property**: Search at https://www.wikidata.org/
   - Common properties: https://www.wikidata.org/wiki/Wikidata:List_of_properties
   
2. **Add to SPARQL query** in `query_wikidata_for_municipality()`:
   ```python
   # Example: Add vice-mayor (if property exists)
   SELECT ?mayor ?mayorLabel ?viceMayor ?viceMayorLabel ...
   
   OPTIONAL { ?city wdt:PXXXX ?viceMayor. }  # Replace PXXXX with actual property
   ```

3. **Parse the result**:
   ```python
   return {
       'mayor_name': result.get('mayorLabel', {}).get('value'),
       'vice_mayor_name': result.get('viceMayorLabel', {}).get('value'),  # Add new field
       # ... other fields
   }
   ```

4. **Add to CSV headers** in `write_to_csv()`:
   ```python
   fieldnames = [
       # ... existing fields
       'vice_mayor_name',  # Add new field
   ]
   ```

### From Wikipedia Infobox

1. **Check Wikipedia template**: https://pt.wikipedia.org/wiki/Predefini%C3%A7%C3%A3o:Info/Munic%C3%ADpio_do_Brasil

2. **Add parsing logic** in `parse_wikipedia_infobox()`:
   ```python
   # Example: Add vice-mayor
   if 'vice-prefeito' in header:
       text = td.get_text(strip=True)
       data['vice_mayor_name'] = text
   ```

3. **Add to CSV headers** as above

## Documentation References

### Wikidata
- Query Service: https://query.wikidata.org/
- SPARQL Tutorial: https://www.wikidata.org/wiki/Wikidata:SPARQL_tutorial
- Property Browser: https://www.wikidata.org/wiki/Wikidata:List_of_properties
- Common Properties:
  * P6 = head of government (prefeito)
  * P31 = instance of
  * P131 = located in administrative territorial entity
  * P102 = member of political party
  * P580 = start time
  * P582 = end time

### Wikipedia
- Infobox template: https://pt.wikipedia.org/wiki/Predefini%C3%A7%C3%A3o:Info/Munic%C3%ADpio_do_Brasil
- Common infobox fields: prefeito, vice-prefeito, população, área, PIB, IDH

## Code Structure

The script is organized in well-documented functions:

1. **`load_estados()`**: Load state data from JSON
2. **`load_municipios()`**: Load municipality data from JSON
3. **`query_wikidata_for_municipality()`**: Query Wikidata SPARQL endpoint
4. **`scrape_wikipedia_for_municipality()`**: Scrape Wikipedia page
5. **`parse_wikipedia_infobox()`**: Parse Wikipedia infobox table
6. **`process_municipalities()`**: Main processing loop
7. **`write_to_csv()`**: Write enriched data to CSV
8. **`main()`**: CLI entry point

Each function includes detailed comments explaining:
- What it does (responsibility)
- How to extend it
- Where to find relevant documentation

## Rate Limiting

The script implements respectful rate limiting:
- **Wikidata**: 0.1 seconds between requests
- **Wikipedia**: 1 second between requests

## Example Workflow

**Using Docker (recommended):**

```bash
# 1. Test with small dataset (CSV)
docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --limit 10 --output test.csv

# 2. Review test.csv to verify data quality

# 3. Test with JSON to verify structure
docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --limit 10 --format json --output test.json

# 4. Process all municipalities (takes hours)
docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --output municipios_complete.csv
# or
docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --format json --output municipios_complete.json

# 5. Import into database or use for analysis
```

## Notes

- The script is **idempotent**: Running it multiple times produces the same results
- All functions have **detailed comments** explaining the code
- **Error handling**: Failed queries are logged and don't stop execution
- **Verbose output**: Shows progress for each municipality

