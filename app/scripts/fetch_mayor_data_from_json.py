#!/usr/bin/env python3
"""
This script is responsible for fetching mayor data from Wikidata and Wikipedia
for Brazilian municipalities and enriching the municipios.json data.

WIKIDATA DOCUMENTATION:
- Query Service: https://query.wikidata.org/
- SPARQL Tutorial: https://www.wikidata.org/wiki/Wikidata:SPARQL_tutorial
- Property Browser: https://www.wikidata.org/wiki/Wikidata:List_of_properties
- Common Properties:
  * P6 = head of government (prefeito)
  * P31 = instance of
  * P131 = located in administrative territorial entity
  * P102 = member of political party
  * P580 = start time (pq:P580 for qualifiers)
  * P582 = end time (pq:P582 for qualifiers)
  
ADDING NEW FIELDS:
1. Find the property on Wikidata (search at wikidata.org)
2. Add OPTIONAL clause in SPARQL query (see query_wikidata_for_municipality function)
3. Parse the result in query_wikidata_for_municipality function
4. Add field to output CSV headers (see write_to_csv function)
5. Add field to data dictionary

WIKIPEDIA INFOBOX FIELDS:
- Template docs: https://pt.wikipedia.org/wiki/Predefini%C3%A7%C3%A3o:Info/Munic%C3%ADpio_do_Brasil
- Common fields in infobox:
  * prefeito/prefeita = mayor name
  * vice-prefeito = vice mayor
  * população = population
  * área = area
  * PIB = GDP
  * IDH = HDI

USAGE EXAMPLES:

# Docker (recommended - default paths work automatically)
docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --limit 10
docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --format json --output output.json

# Local (from app directory - requires custom paths)
cd /path/to/app
python scripts/fetch_mayor_data_from_json.py --limit 10 \\
    --municipios ../data/municipios-brasileiros/json/municipios.json \\
    --estados ../data/municipios-brasileiros/json/estados.json

# Export to JSON format (Docker)
docker compose run --rm app python scripts/fetch_mayor_data_from_json.py \\
    --format json --output municipios_enriched.json

# Skip Wikidata (Wikipedia only)
docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --skip-wikidata
"""

import json
import csv
import argparse
import logging
import time
import re
from typing import Optional, Dict, Any, List
from urllib.parse import quote
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from SPARQLWrapper import SPARQLWrapper, JSON

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_estados(estados_path: str) -> Dict[int, Dict[str, Any]]:
    """
    This function is responsible for loading estados.json and creating 
    a lookup dictionary by codigo_uf for fast state lookups.
    
    Args:
        estados_path: Path to estados.json file
        
    Returns:
        Dictionary mapping codigo_uf to state data
        Example: {11: {uf: "RO", nome: "Rondônia", ...}, ...}
    """
    # Use utf-8-sig to handle potential BOM (Byte Order Mark) in JSON files
    with open(estados_path, 'r', encoding='utf-8-sig') as f:
        estados = json.load(f)
    return {estado['codigo_uf']: estado for estado in estados}


def load_municipios(municipios_path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    This function is responsible for loading municipios.json with optional 
    limit for testing purposes.
    
    Args:
        municipios_path: Path to municipios.json file
        limit: Optional limit for number of municipalities to load
        
    Returns:
        List of municipality dictionaries
    """
    # Use utf-8-sig to handle potential BOM (Byte Order Mark) in JSON files
    with open(municipios_path, 'r', encoding='utf-8-sig') as f:
        municipios = json.load(f)
    
    if limit:
        municipios = municipios[:limit]
        logger.info(f'Limited to {limit} municipalities for testing')
    
    return municipios


def extract_year(date_string: Optional[str]) -> Optional[int]:
    """
    This function is responsible for extracting a year from Wikidata date strings.
    Wikidata dates are usually in format YYYY-MM-DD or +YYYY-MM-DD.
    
    Args:
        date_string: Date string from Wikidata
        
    Returns:
        Integer year or None if extraction fails
    """
    if not date_string:
        return None
    try:
        match = re.search(r'\d{4}', date_string)
        if match:
            return int(match.group(0))
    except (ValueError, AttributeError):
        pass
    return None


def query_wikidata_for_municipality(
    sparql: SPARQLWrapper, 
    municipio: Dict[str, Any], 
    estado: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    This function is responsible for querying Wikidata SPARQL endpoint
    to fetch mayor data for a specific municipality.
    
    SPARQL QUERY STRUCTURE:
    - SELECT: defines what variables to return (?mayor, ?mayorLabel, etc.)
    - WHERE: defines patterns to match in the graph
    - OPTIONAL: allows missing data (won't fail if party is absent)
    - SERVICE wikibase:label: automatically fetches human-readable labels
    - FILTER: restricts results (language, state matching)
    
    TO ADD MORE FIELDS:
    1. Add variable to SELECT clause (e.g., ?viceMayor ?viceMayorLabel)
    2. Add OPTIONAL clause in WHERE block:
       Example: OPTIONAL { ?city wdt:P1313 ?viceMayor. }  # P1313 = office held by head of government
    3. Parse the result below in the return dictionary
    4. Add the field to CSV output in write_to_csv function
    
    Wikidata Items (Q-codes):
    - Q3184121 = municipality of Brazil
    - Q485258 = state of Brazil
    
    Wikidata Properties (P-codes) used here:
    - P6 = head of government
    - P31 = instance of
    - P131 = located in administrative territorial entity
    - P102 = member of political party
    - P580 = start time (as qualifier)
    - P582 = end time (as qualifier)
    
    Args:
        sparql: Configured SPARQLWrapper instance
        municipio: Municipality data from JSON
        estado: State data from JSON
        
    Returns:
        Dictionary with mayor data or None if not found
    """
    nome = municipio['nome']
    estado_abbr = estado['uf']
    estado_nome = estado['nome']
    
    # Build SPARQL query
    query = f"""
    SELECT ?mayor ?mayorLabel ?party ?partyLabel ?startDate ?endDate WHERE {{
      ?city wdt:P31 wd:Q3184121;  # instance of municipality of Brazil
            rdfs:label "{nome}"@pt;
            wdt:P131* ?state.
      ?state wdt:P31 wd:Q485258;  # instance of state of Brazil
             rdfs:label ?stateLabel.
      FILTER(LANG(?stateLabel) = "pt")
      FILTER(CONTAINS(?stateLabel, "{estado_abbr}") || CONTAINS(?stateLabel, "{estado_nome}"))
      
      ?city wdt:P6 ?mayor.  # head of government (P6 is the property for head of government)
      OPTIONAL {{ ?mayor wdt:P102 ?party. }}  # P102 = member of political party
      OPTIONAL {{
        ?city p:P6 ?statement.
        ?statement ps:P6 ?mayor.
        OPTIONAL {{ ?statement pq:P580 ?startDate. }}  # P580 = start time
        OPTIONAL {{ ?statement pq:P582 ?endDate. }}    # P582 = end time
      }}
      
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
    }}
    ORDER BY DESC(?startDate)
    LIMIT 1
    """
    
    sparql.setQuery(query)
    
    try:
        results = sparql.query().convert()
        bindings = results.get('results', {}).get('bindings', [])
        
        if bindings:
            result = bindings[0]
            return {
                'mayor_name': result.get('mayorLabel', {}).get('value'),
                'mayor_party': result.get('partyLabel', {}).get('value'),
                'mayor_mandate_start': extract_year(result.get('startDate', {}).get('value')),
                'mayor_mandate_end': extract_year(result.get('endDate', {}).get('value')),
                'data_source': 'wikidata'
            }
    except Exception as e:
        error_msg = str(e)
        # Detect proxy/connection issues
        if 'Connection' in error_msg or 'Proxy' in error_msg or 'Errno 104' in error_msg:
            logger.warning(f'⚠️  Connection error for {nome}: {error_msg}')
            logger.warning('   Hint: Check proxy settings if running in proxied environment')
        else:
            logger.debug(f'Wikidata query failed for {nome}: {error_msg}')
        return None
    
    return None


def parse_wikipedia_infobox(html: str, url: str) -> Optional[Dict[str, Any]]:
    """
    This function is responsible for parsing the Wikipedia infobox table
    and extracting structured data from it.
    
    Wikipedia infoboxes use the template "Info/Município do Brasil".
    The table has rows with <th> (header) and <td> (data) elements.
    
    TO ADD MORE FIELDS FROM INFOBOX:
    1. Inspect the Wikipedia page's infobox HTML
    2. Add a new condition in the loop below (check the header text)
    3. Parse the text content from the <td> element
    4. Use regex if needed for structured data extraction
    
    Common infobox fields:
    - prefeito/prefeita: Mayor name
    - vice-prefeito: Vice mayor
    - população: Population
    - área: Area in km²
    - PIB: GDP
    - IDH: Human Development Index
    
    Args:
        html: HTML content of Wikipedia page
        url: URL of the Wikipedia page (for reference)
        
    Returns:
        Dictionary with parsed data or None if no infobox found
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find infobox
    infobox = soup.find('table', {'class': 'infobox'})
    if not infobox:
        return None
    
    data = {'wikipedia_url': url}
    
    # Look for mayor information in table rows
    rows = infobox.find_all('tr')
    for row in rows:
        # Wikipedia uses both <th> and <td scope="row"> for headers
        th = row.find('th')
        tds = row.find_all('td')
        
        # Case 1: <th> + <td> structure
        if th and len(tds) >= 1:
            header_cell = th
            data_cell = tds[0]
        # Case 2: <td scope="row"> + <td> structure (2+ td elements)
        elif len(tds) >= 2:
            # First td with scope="row" is the header
            first_td = tds[0]
            if first_td.get('scope') == 'row':
                header_cell = first_td
                data_cell = tds[1]
            else:
                continue
        else:
            continue
        
        header = header_cell.get_text(strip=True).lower()
        td = data_cell
        
        # Mayor name (prefeito/prefeita field in infobox)
        if 'prefeito' in header or 'prefeita' in header:
            text = td.get_text(separator=' ', strip=True)
            
            # Extract name (usually first line or before party info)
            name_match = re.match(r'^([^(\n]+)', text)
            if name_match:
                data['mayor_name'] = name_match.group(1).strip()
            
            # Extract party - handles multiple formats:
            # - Standalone: (PT) or (PSDB)
            # - With dates: (PT, 2021–2024) or ( PP , 2025–2028)
            # Pattern matches 2+ uppercase letters, optionally followed by -/LETTERS
            # Handles spaces: ( PP , or (PP,
            party_match = re.search(r'\(\s*([A-Z]{2,}(?:[-/][A-Z]{2,})?)\s*[,)]', text)
            if party_match:
                data['mayor_party'] = party_match.group(1)
            
            # Extract mandate years (pattern: 2021–2024 or 2021-2024)
            # Handles different dash types: hyphen, en-dash, em-dash
            mandate_match = re.search(r'(\d{4})\s*[-–—]\s*(\d{4})', text)
            if mandate_match:
                data['mayor_mandate_start'] = int(mandate_match.group(1))
                data['mayor_mandate_end'] = int(mandate_match.group(2))
    
    # Return data only if we found at least the mayor name
    return data if 'mayor_name' in data else None


def scrape_wikipedia_for_municipality(
    municipio: Dict[str, Any], 
    estado: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    This function is responsible for scraping Wikipedia infobox
    to extract mayor data when Wikidata doesn't have the information.
    
    Uses Wikipedia API (action=query) to:
    1. Find the correct page title (handles redirects automatically)
    2. Fetch the HTML content
    3. Parse the infobox
    
    Wikipedia API docs: https://www.mediawiki.org/wiki/API:Main_page
    
    Args:
        municipio: Municipality data from JSON
        estado: State data from JSON
        
    Returns:
        Dictionary with mayor data or None if not found
    """
    nome = municipio['nome']
    estado_abbr = estado['uf']
    
    headers = {
        'User-Agent': 'MunicipalityDataBot/1.0 (Educational Purpose)'
    }
    
    # Try different search terms
    search_terms = [
        nome,  # Most common case
        f"{nome} ({estado_abbr})",  # Disambiguation pages
        f"{nome} {estado_abbr}",  # Alternative format
    ]
    
    for search_term in search_terms:
        try:
            # Step 1: Use Wikipedia API to search for the page
            api_url = "https://pt.wikipedia.org/w/api.php"
            params = {
                'action': 'query',
                'titles': search_term,
                'prop': 'info',
                'inprop': 'url',
                'redirects': '1',  # Follow redirects automatically
                'format': 'json'
            }
            
            response = requests.get(api_url, params=params, headers=headers, timeout=10)
            if response.status_code != 200:
                continue
            
            api_data = response.json()
            pages = api_data.get('query', {}).get('pages', {})
            
            # Check if page exists (missing pages have negative page IDs)
            page_data = next(iter(pages.values()), {})
            if int(page_data.get('pageid', -1)) < 0:
                continue  # Page doesn't exist
            
            # Step 2: Fetch the actual HTML content
            page_title = page_data.get('title')
            page_url = f"https://pt.wikipedia.org/wiki/{quote(page_title.replace(' ', '_'))}"
            
            html_response = requests.get(page_url, headers=headers, timeout=10)
            if html_response.status_code == 200:
                data = parse_wikipedia_infobox(html_response.text, page_url)
                if data:
                    data['data_source'] = 'wikipedia'
                    logger.debug(f'Found Wikipedia page: {page_url}')
                    return data
                
        except requests.RequestException as e:
            error_msg = str(e)
            if 'Connection' in error_msg or 'Proxy' in error_msg:
                logger.warning(f'⚠️  Connection error for {search_term}: {error_msg}')
            else:
                logger.debug(f'Wikipedia request failed for {search_term}: {error_msg}')
            continue
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.debug(f'Wikipedia API parsing error for {search_term}: {e}')
            continue
    
    return None


def process_municipalities(
    municipios: List[Dict[str, Any]],
    estados_lookup: Dict[int, Dict[str, Any]],
    skip_wikidata: bool = False,
    skip_wikipedia: bool = False,
    success_only: bool = False,
    one_per_source: bool = False
) -> List[Dict[str, Any]]:
    """
    This function is responsible for processing all municipalities
    and enriching them with mayor data from Wikidata and Wikipedia.
    
    Strategy:
    1. Try Wikidata first (faster, more structured)
    2. Fallback to Wikipedia if Wikidata has no data
    3. Merge mayor data with original municipality data
    
    Args:
        municipios: List of municipality dictionaries from JSON
        estados_lookup: Dictionary mapping codigo_uf to state data
        skip_wikidata: If True, skip Wikidata queries
        skip_wikipedia: If True, skip Wikipedia scraping
        success_only: If True, only return municipalities with data found
        one_per_source: If True, stop after finding one result per source
        
    Returns:
        List of enriched municipality dictionaries
    """
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setReturnFormat(JSON)
    
    results = []
    stats = {
        'total': len(municipios),
        'wikidata_success': 0,
        'wikipedia_success': 0,
        'failed': 0
    }
    
    # For one_per_source mode: track if we found examples
    found_wikidata_example = False
    found_wikipedia_example = False
    
    for idx, municipio in enumerate(municipios, 1):
        nome = municipio['nome']
        codigo_uf = municipio['codigo_uf']
        estado = estados_lookup.get(codigo_uf)
        
        if not estado:
            logger.warning(f"[{idx}/{stats['total']}] No state found for {nome}")
            if not success_only:  # Skip if success_only mode
                results.append({**municipio, 'data_source': 'none'})
            stats['failed'] += 1
            continue
        
        # Skip if one_per_source mode and we already found both
        if one_per_source and found_wikidata_example and found_wikipedia_example:
            logger.info(f"[{idx}/{stats['total']}] Stopping - found one example per source")
            break
        
        logger.info(f"[{idx}/{stats['total']}] Processing {nome} ({estado['uf']})...")
        
        mayor_data = None
        
        # Try Wikidata first (unless we already have an example in one_per_source mode)
        if not skip_wikidata and not (one_per_source and found_wikidata_example):
            mayor_data = query_wikidata_for_municipality(sparql, municipio, estado)
            if mayor_data:
                stats['wikidata_success'] += 1
                found_wikidata_example = True
                logger.info(f"  ✓ Wikidata: {mayor_data.get('mayor_name', 'N/A')}")
            time.sleep(0.1)  # Rate limiting - be respectful to Wikidata
        
        # Fallback to Wikipedia if Wikidata didn't find data
        # (or skip if we already have Wikipedia example in one_per_source mode)
        if not mayor_data and not skip_wikipedia and not (one_per_source and found_wikipedia_example):
            mayor_data = scrape_wikipedia_for_municipality(municipio, estado)
            if mayor_data:
                stats['wikipedia_success'] += 1
                found_wikipedia_example = True
                logger.info(f"  ✓ Wikipedia: {mayor_data.get('mayor_name', 'N/A')}")
            time.sleep(1)  # Rate limiting - 1 request per second for Wikipedia
        
        # Merge data with original municipality data
        if mayor_data:
            enriched = {**municipio, **mayor_data}
            results.append(enriched)
        else:
            if not success_only:  # Only add failed entries if not in success_only mode
                enriched = {**municipio, 'data_source': 'none'}
                results.append(enriched)
            stats['failed'] += 1
            logger.info(f"  - No data found")
    
    # Print statistics
    logger.info("\n=== SUMMARY ===")
    logger.info(f"Total: {stats['total']}")
    logger.info(f"Wikidata: {stats['wikidata_success']}")
    logger.info(f"Wikipedia: {stats['wikipedia_success']}")
    logger.info(f"Failed: {stats['failed']}")
    
    return results


def write_to_csv(data: List[Dict[str, Any]], output_path: str):
    """
    This function is responsible for writing the enriched municipality data
    to a CSV file with all original fields plus new mayor fields.
    
    TO ADD NEW FIELDS TO CSV:
    1. Add the field name to the fieldnames list below
    2. Ensure the field is present in the data dictionaries
    3. The csv.DictWriter will handle the rest automatically
       (extrasaction='ignore' means extra fields in data are ignored)
    
    Args:
        data: List of enriched municipality dictionaries
        output_path: Path where CSV file should be written
    """
    if not data:
        logger.warning("No data to write")
        return
    
    # Define all possible fields (original + new)
    # Order matters for CSV column order
    fieldnames = [
        # Original fields from municipios.json
        'codigo_ibge',
        'nome',
        'latitude',
        'longitude',
        'capital',
        'codigo_uf',
        'siafi_id',
        'ddd',
        'fuso_horario',
        # New mayor fields
        'mayor_name',
        'mayor_party',
        'mayor_mandate_start',
        'mayor_mandate_end',
        'wikipedia_url',
        'data_source'
    ]
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
    
    logger.info(f"✓ CSV written to: {output_path}")


def write_to_json(data: List[Dict[str, Any]], output_path: str):
    """
    This function is responsible for writing the enriched municipality data
    to a JSON file with all fields.
    
    JSON format preserves data types (integers, nulls) better than CSV.
    Useful for importing into other systems or further processing.
    
    Args:
        data: List of enriched municipality dictionaries
        output_path: Path where JSON file should be written
    """
    if not data:
        logger.warning("No data to write")
        return
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✓ JSON written to: {output_path}")


def main():
    """
    Main entry point for the script.
    Handles command-line arguments and orchestrates the data fetching process.
    """
    parser = argparse.ArgumentParser(
        description='Fetch mayor data for Brazilian municipalities from Wikidata/Wikipedia',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples (Docker - recommended):
  # Test with 10 municipalities (CSV)
  docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --limit 10
  
  # Get one example from each source (Wikidata + Wikipedia)
  docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --one-per-source --success-only
  
  # Process all municipalities, only save successes
  docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --success-only --output successful_only.csv
  
  # Export to JSON format
  docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --format json --output output.json
  
  # Skip Wikidata (Wikipedia only)
  docker compose run --rm app python scripts/fetch_mayor_data_from_json.py --skip-wikidata
        """
    )
    parser.add_argument(
        '--municipios',
        default='/data/municipios-brasileiros/json/municipios.json',
        help='Path to municipios.json (default: /data/municipios-brasileiros/json/municipios.json)'
    )
    parser.add_argument(
        '--estados',
        default='/data/municipios-brasileiros/json/estados.json',
        help='Path to estados.json (default: /data/municipios-brasileiros/json/estados.json)'
    )
    parser.add_argument(
        '--output',
        default='municipios_enriched.csv',
        help='Output file path (default: municipios_enriched.csv)'
    )
    parser.add_argument(
        '--format',
        choices=['csv', 'json'],
        default='csv',
        help='Output format: csv or json (default: csv)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of municipalities (for testing)'
    )
    parser.add_argument(
        '--skip-wikidata',
        action='store_true',
        help='Skip Wikidata queries'
    )
    parser.add_argument(
        '--skip-wikipedia',
        action='store_true',
        help='Skip Wikipedia scraping'
    )
    parser.add_argument(
        '--success-only',
        action='store_true',
        help='Only output municipalities with data found (excludes failed entries)'
    )
    parser.add_argument(
        '--one-per-source',
        action='store_true',
        help='Stop after finding one successful result from each source (Wikidata and Wikipedia)'
    )
    
    args = parser.parse_args()
    
    # Test connectivity before processing
    logger.info("Testing network connectivity...")
    try:
        response = requests.get('https://www.wikidata.org', timeout=5)
        logger.info("✓ Network connectivity OK")
    except requests.RequestException as e:
        logger.error(f"❌ Network connectivity test failed: {e}")
        logger.error("Hint: If behind proxy, ensure HTTP_PROXY/HTTPS_PROXY env vars are set")
        logger.error("Example: export HTTP_PROXY=http://proxy:8080")
        logger.error("Continuing anyway, but requests will likely fail...")
    
    # Load data
    logger.info("Loading data files...")
    try:
        estados_lookup = load_estados(args.estados)
        logger.info(f"✓ Loaded {len(estados_lookup)} states")
    except FileNotFoundError:
        logger.error(f"Estados file not found: {args.estados}")
        return
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in estados file: {args.estados}")
        return
    
    try:
        municipios = load_municipios(args.municipios, args.limit)
        logger.info(f"✓ Loaded {len(municipios)} municipalities")
    except FileNotFoundError:
        logger.error(f"Municipios file not found: {args.municipios}")
        return
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in municipios file: {args.municipios}")
        return
    
    # Process
    logger.info(f"\nProcessing {len(municipios)} municipalities...")
    if args.one_per_source:
        logger.info("Mode: One example per source (will stop after finding Wikidata + Wikipedia examples)")
    if args.success_only:
        logger.info("Mode: Success only (will exclude municipalities without data)")
    
    enriched_data = process_municipalities(
        municipios,
        estados_lookup,
        skip_wikidata=args.skip_wikidata,
        skip_wikipedia=args.skip_wikipedia,
        success_only=args.success_only,
        one_per_source=args.one_per_source
    )
    
    # Write output in requested format
    if args.format == 'json':
        write_to_json(enriched_data, args.output)
    else:
        write_to_csv(enriched_data, args.output)
    
    logger.info("\nDone!")


if __name__ == '__main__':
    main()

