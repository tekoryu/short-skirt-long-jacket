import re
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from SPARQLWrapper import SPARQLWrapper, JSON

from apps.cities.models import Municipality

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch mayor data (name, party, mandate) from Wikidata and Wikipedia for Brazilian municipalities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit the number of municipalities to process (for testing)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without saving data to database',
        )
        parser.add_argument(
            '--skip-wikidata',
            action='store_true',
            help='Skip Wikidata queries and go straight to Wikipedia',
        )
        parser.add_argument(
            '--skip-wikipedia',
            action='store_true',
            help='Skip Wikipedia scraping',
        )

    def handle(self, *args, **options):
        limit = options.get('limit')
        dry_run = options.get('dry_run', False)
        skip_wikidata = options.get('skip_wikidata', False)
        skip_wikipedia = options.get('skip_wikipedia', False)

        self.stdout.write(self.style.SUCCESS('Starting mayor data collection...'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))

        # Get municipalities
        municipalities_qs = Municipality.objects.select_related(
            'immediate_region__intermediate_region__state'
        ).all()
        
        if limit:
            municipalities_qs = municipalities_qs[:limit]
            municipalities = list(municipalities_qs)
            self.stdout.write(f'Processing {limit} municipalities (limit applied)')
        else:
            municipalities = list(municipalities_qs)
            self.stdout.write(f'Processing all {len(municipalities)} municipalities')

        # Statistics
        stats = {
            'total': len(municipalities),
            'wikidata_success': 0,
            'wikipedia_success': 0,
            'failed': 0,
        }

        # Phase 1: Wikidata (batch queries)
        if not skip_wikidata:
            self.stdout.write(self.style.SUCCESS('\n=== Phase 1: Querying Wikidata ==='))
            stats = self._process_wikidata(municipalities, dry_run, stats)

        # Phase 2: Wikipedia scraping (for remaining municipalities)
        if not skip_wikipedia:
            self.stdout.write(self.style.SUCCESS('\n=== Phase 2: Scraping Wikipedia ==='))
            remaining = [m for m in municipalities if not m.mayor_name]
            self.stdout.write(f'Processing {len(remaining)} municipalities without data')
            stats = self._process_wikipedia(remaining, dry_run, stats)

        # Print summary
        self.stdout.write(self.style.SUCCESS('\n=== Summary ==='))
        self.stdout.write(f'Total municipalities: {stats["total"]}')
        self.stdout.write(f'Wikidata successes: {stats["wikidata_success"]}')
        self.stdout.write(f'Wikipedia successes: {stats["wikipedia_success"]}')
        self.stdout.write(f'Failed: {stats["failed"]}')
        self.stdout.write(self.style.SUCCESS('\nData collection complete!'))

    def _process_wikidata(self, municipalities, dry_run, stats):
        """Process municipalities using Wikidata SPARQL queries"""
        sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
        sparql.setReturnFormat(JSON)
        
        # Process in batches
        batch_size = 50
        total = len(municipalities)
        
        for i in range(0, total, batch_size):
            batch = municipalities[i:i + batch_size]
            self.stdout.write(f'Processing batch {i//batch_size + 1} ({i+1}-{min(i+batch_size, total)} of {total})')
            
            for municipality in batch:
                try:
                    data = self._query_wikidata_for_municipality(sparql, municipality)
                    if data:
                        if not dry_run:
                            self._save_municipality_data(municipality, data, source='wikidata')
                        stats['wikidata_success'] += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ {municipality.name}: {data.get("mayor_name", "N/A")}')
                        )
                    else:
                        self.stdout.write(f'  - {municipality.name}: No data in Wikidata')
                except Exception as e:
                    logger.error(f'Wikidata error for {municipality.name}: {str(e)}')
                    self.stdout.write(self.style.ERROR(f'  ✗ {municipality.name}: {str(e)}'))
                
                # Be respectful to Wikidata
                time.sleep(0.1)
        
        return stats

    def _query_wikidata_for_municipality(self, sparql, municipality) -> Optional[Dict[str, Any]]:
        """Query Wikidata for a specific municipality's mayor data"""
        state_abbr = municipality.immediate_region.intermediate_region.state.abbreviation
        
        # Build SPARQL query
        query = f"""
        SELECT ?mayor ?mayorLabel ?party ?partyLabel ?startDate ?endDate WHERE {{
          ?city wdt:P31 wd:Q3184121;  # instance of municipality of Brazil
                rdfs:label "{municipality.name}"@pt;
                wdt:P131* ?state.
          ?state wdt:P31 wd:Q485258;  # instance of state of Brazil
                 rdfs:label ?stateLabel.
          FILTER(LANG(?stateLabel) = "pt")
          FILTER(CONTAINS(?stateLabel, "{state_abbr}") || CONTAINS(?stateLabel, "{municipality.immediate_region.intermediate_region.state.name}"))
          
          ?city wdt:P6 ?mayor.  # head of government
          OPTIONAL {{ ?mayor wdt:P102 ?party. }}
          OPTIONAL {{
            ?city p:P6 ?statement.
            ?statement ps:P6 ?mayor.
            OPTIONAL {{ ?statement pq:P580 ?startDate. }}
            OPTIONAL {{ ?statement pq:P582 ?endDate. }}
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
                    'mayor_mandate_start': self._extract_year(result.get('startDate', {}).get('value')),
                    'mayor_mandate_end': self._extract_year(result.get('endDate', {}).get('value')),
                }
        except Exception as e:
            logger.debug(f'Wikidata query failed for {municipality.name}: {str(e)}')
            return None
        
        return None

    def _process_wikipedia(self, municipalities, dry_run, stats):
        """Process municipalities by scraping Wikipedia"""
        total = len(municipalities)
        
        for idx, municipality in enumerate(municipalities, 1):
            self.stdout.write(f'[{idx}/{total}] Processing {municipality.name}...')
            
            try:
                data = self._scrape_wikipedia_for_municipality(municipality)
                if data:
                    if not dry_run:
                        self._save_municipality_data(municipality, data, source='wikipedia')
                    stats['wikipedia_success'] += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Found: {data.get("mayor_name", "N/A")} ({data.get("mayor_party", "N/A")})')
                    )
                else:
                    stats['failed'] += 1
                    self.stdout.write(f'  - No data found')
            except Exception as e:
                stats['failed'] += 1
                logger.error(f'Wikipedia error for {municipality.name}: {str(e)}')
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
            
            # Rate limiting: 1 request per second
            time.sleep(1)
        
        return stats

    def _scrape_wikipedia_for_municipality(self, municipality) -> Optional[Dict[str, Any]]:
        """Scrape Wikipedia page for municipality mayor data"""
        state_abbr = municipality.immediate_region.intermediate_region.state.abbreviation
        
        # Try different URL patterns
        url_patterns = [
            f"https://pt.wikipedia.org/wiki/{quote(municipality.name)}_{quote(state_abbr)}",
            f"https://pt.wikipedia.org/wiki/{quote(municipality.name)}_({quote(state_abbr)})",
            f"https://pt.wikipedia.org/wiki/{quote(municipality.name)}",
        ]
        
        headers = {
            'User-Agent': 'MunicipalityDataBot/1.0 (Educational Purpose; Django App)'
        }
        
        for url in url_patterns:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = self._parse_wikipedia_infobox(response.text, url)
                    if data:
                        return data
            except requests.RequestException:
                continue
        
        return None

    def _parse_wikipedia_infobox(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Parse Wikipedia infobox for mayor information"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find infobox
        infobox = soup.find('table', {'class': 'infobox'})
        if not infobox:
            return None
        
        data = {'wikipedia_url': url}
        
        # Look for mayor information in table rows
        rows = infobox.find_all('tr')
        for row in rows:
            th = row.find('th')
            td = row.find('td')
            
            if not th or not td:
                continue
            
            header = th.get_text(strip=True).lower()
            
            # Mayor name
            if 'prefeito' in header or 'prefeita' in header:
                # Get text content
                text = td.get_text(separator=' ', strip=True)
                
                # Extract name (usually first line or before party info)
                name_match = re.match(r'^([^(\n]+)', text)
                if name_match:
                    data['mayor_name'] = name_match.group(1).strip()
                
                # Extract party (usually in parentheses)
                party_match = re.search(r'\(([A-Z]{2,}(?:[-/][A-Z]{2,})?)\)', text)
                if party_match:
                    data['mayor_party'] = party_match.group(1)
                
                # Extract mandate years
                mandate_match = re.search(r'(\d{4})\s*[-–—]\s*(\d{4})', text)
                if mandate_match:
                    data['mayor_mandate_start'] = int(mandate_match.group(1))
                    data['mayor_mandate_end'] = int(mandate_match.group(2))
                else:
                    # Try to find single year or year range in separate rows
                    mandate_text = td.get_text(separator='\n', strip=True)
                    years = re.findall(r'\b(20\d{2})\b', mandate_text)
                    if len(years) >= 2:
                        data['mayor_mandate_start'] = int(years[-2])
                        data['mayor_mandate_end'] = int(years[-1])
        
        # Return data only if we found at least the mayor name
        return data if 'mayor_name' in data else None

    def _save_municipality_data(self, municipality: Municipality, data: Dict[str, Any], source: str):
        """Save mayor data to municipality"""
        municipality.mayor_name = data.get('mayor_name')
        municipality.mayor_party = data.get('mayor_party')
        municipality.mayor_mandate_start = data.get('mayor_mandate_start')
        municipality.mayor_mandate_end = data.get('mayor_mandate_end')
        if data.get('wikipedia_url'):
            municipality.wikipedia_url = data.get('wikipedia_url')
        municipality.mayor_data_updated_at = timezone.now()
        municipality.save(update_fields=[
            'mayor_name', 'mayor_party', 'mayor_mandate_start', 
            'mayor_mandate_end', 'wikipedia_url', 'mayor_data_updated_at'
        ])

    def _extract_year(self, date_string: Optional[str]) -> Optional[int]:
        """Extract year from date string"""
        if not date_string:
            return None
        try:
            # Wikidata dates are usually in format YYYY-MM-DD or +YYYY-MM-DD
            match = re.search(r'\d{4}', date_string)
            if match:
                return int(match.group(0))
        except (ValueError, AttributeError):
            pass
        return None

