"""
This class is responsible for importing Wikipedia infobox data into the Municipality model.
"""
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.cities.models import Municipality


class Command(BaseCommand):
    """This class is responsible for importing Wikipedia infobox data for municipalities."""
    
    help = 'Import Wikipedia infobox data into municipalities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='/app/data/scraping/wikipedia_infobox_data.json',
            help='Path to the Wikipedia JSON file'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        
        self.stdout.write(self.style.SUCCESS(f'Loading data from {file_path}...'))
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                wiki_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Invalid JSON: {e}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(wiki_data)} entries'))
        
        # Statistics
        stats = {
            'total': len(wiki_data),
            'matched': 0,
            'updated': 0,
            'no_infobox': 0,
            'not_found': 0,
        }
        
        municipalities_to_update = []
        now = timezone.now()
        
        for entry in wiki_data:
            codigo_ibge = str(entry.get('codigo_ibge'))
            infobox_data = entry.get('infobox_data')
            
            if not infobox_data:
                stats['no_infobox'] += 1
                continue
            
            # Try to find the municipality by code
            try:
                municipality = Municipality.objects.get(code=codigo_ibge)
                stats['matched'] += 1
            except Municipality.DoesNotExist:
                stats['not_found'] += 1
                continue
            
            # Extract data with multiple field name variants
            municipality.wiki_demonym = self._extract_field(infobox_data, ['Gentílico'])
            municipality.wiki_altitude = self._extract_field(infobox_data, ['Altitude'])
            municipality.wiki_total_area = self._extract_field(infobox_data, ['Área total'])
            municipality.wiki_population = self._extract_field(infobox_data, ['População total'])
            municipality.wiki_density = self._extract_field(infobox_data, ['Densidade'])
            municipality.wiki_climate = self._extract_field(infobox_data, ['Clima'])
            municipality.wiki_idh = self._extract_field(infobox_data, ['IDH'])
            municipality.wiki_gdp = self._extract_field(infobox_data, ['PIB'])
            municipality.wiki_gdp_per_capita = self._extract_field(infobox_data, ['PIBper capita', 'PIB per capita'])
            municipality.wiki_website = self._extract_field(infobox_data, ['Sítio'])
            municipality.wiki_metropolitan_region = self._extract_field(infobox_data, ['Região metropolitana'])
            municipality.wiki_bordering_municipalities = self._extract_field(infobox_data, ['Municípios limítrofes'])
            municipality.wiki_distance_to_capital = self._extract_field(infobox_data, ['Distância até acapital', 'Distância até a capital'])
            municipality.wiki_foundation_date = self._extract_field(infobox_data, ['Fundação'])
            municipality.wiki_council_members = self._extract_field(infobox_data, ['Vereadores'])
            municipality.wiki_postal_code = self._extract_field(infobox_data, ['CEP'])
            municipality.wiki_gini = self._extract_field(infobox_data, ['Gini'])
            
            # Mayor information from Wikipedia
            municipality.wiki_mayor_name = infobox_data.get('prefeito_nome')
            municipality.wiki_mayor_party = infobox_data.get('prefeito_partido')
            municipality.wiki_mayor_mandate_start = infobox_data.get('prefeito_mandato_inicio')
            municipality.wiki_mayor_mandate_end = infobox_data.get('prefeito_mandato_fim')
            
            municipality.wiki_data_updated_at = now
            
            municipalities_to_update.append(municipality)
            stats['updated'] += 1
        
        # Bulk update
        if municipalities_to_update:
            self.stdout.write(self.style.SUCCESS(f'Updating {len(municipalities_to_update)} municipalities...'))
            Municipality.objects.bulk_update(
                municipalities_to_update,
                [
                    'wiki_demonym',
                    'wiki_altitude',
                    'wiki_total_area',
                    'wiki_population',
                    'wiki_density',
                    'wiki_climate',
                    'wiki_idh',
                    'wiki_gdp',
                    'wiki_gdp_per_capita',
                    'wiki_website',
                    'wiki_metropolitan_region',
                    'wiki_bordering_municipalities',
                    'wiki_distance_to_capital',
                    'wiki_foundation_date',
                    'wiki_council_members',
                    'wiki_postal_code',
                    'wiki_gini',
                    'wiki_mayor_name',
                    'wiki_mayor_party',
                    'wiki_mayor_mandate_start',
                    'wiki_mayor_mandate_end',
                    'wiki_data_updated_at',
                ],
                batch_size=500
            )
        
        # Print statistics
        self.stdout.write(self.style.SUCCESS('\n--- Import Statistics ---'))
        self.stdout.write(f"Total entries in JSON: {stats['total']}")
        self.stdout.write(f"Entries without infobox data: {stats['no_infobox']}")
        self.stdout.write(f"Municipalities matched: {stats['matched']}")
        self.stdout.write(f"Municipalities updated: {stats['updated']}")
        self.stdout.write(f"Municipalities not found in DB: {stats['not_found']}")
        self.stdout.write(self.style.SUCCESS('\nImport completed successfully!'))

    def _extract_field(self, infobox_data, field_names):
        """
        This method is responsible for extracting a field from infobox data.
        It searches for exact matches and partial matches (for fields with variations like IDH(PNUD/2010[3])).
        """
        # Try exact matches first
        for field_name in field_names:
            if field_name in infobox_data:
                value = infobox_data[field_name]
                if value:
                    return str(value).strip()
        
        # Try partial matches (for fields with variants like "IDH(PNUD/2010[3])")
        for field_name in field_names:
            for key in infobox_data.keys():
                if key.startswith(field_name):
                    value = infobox_data[key]
                    if value:
                        return str(value).strip()
        
        return None








