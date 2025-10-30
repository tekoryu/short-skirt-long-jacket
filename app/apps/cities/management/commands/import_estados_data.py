import csv
import logging
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.cities.models import Region, State

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import Brazilian states data from estados.csv file'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='/app/data/repo/estados.csv',
            help='Path to the estados.csv file (default: /app/data/repo/estados.csv)'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing states data before importing'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        file_path = options['file']
        clear_existing = options['clear_existing']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting estados data import at {start_time}')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No data will be imported')
            )
        
        try:
            # Clear existing data if requested
            if clear_existing and not dry_run:
                self.clear_existing_data()
            
            # Import data
            imported_count = self.import_data(file_path, dry_run)
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Import completed successfully!\n'
                    f'States processed: {imported_count}\n'
                    f'Duration: {duration:.2f} seconds'
                )
            )
            
        except FileNotFoundError:
            raise CommandError(f'CSV file not found: {file_path}')
        except Exception as e:
            logger.error(f'Error during import: {str(e)}')
            raise CommandError(f'Import failed: {str(e)}')
    
    def clear_existing_data(self):
        """Clear all existing states data"""
        self.stdout.write('Clearing existing states data...')
        
        states_deleted = State.objects.count()
        State.objects.all().delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Deleted {states_deleted} states')
        )
    
    def get_or_create_region(self, region_name, dry_run):
        """Get or create a region by name"""
        if dry_run:
            try:
                return Region.objects.get(name=region_name)
            except Region.DoesNotExist:
                return None
        
        # Map region names to codes
        region_codes = {
            'Norte': 'N',
            'Nordeste': 'NE',
            'Sudeste': 'SE',
            'Sul': 'S',
            'Centro-Oeste': 'CO'
        }
        
        region_code = region_codes.get(region_name, region_name[:2].upper())
        region, created = Region.objects.get_or_create(
            name=region_name,
            defaults={'code': region_code}
        )
        
        if created:
            self.stdout.write(f'Created region: {region_name} ({region_code})')
        
        return region
    
    def import_data(self, file_path, dry_run):
        """Import data from estados.csv file"""
        states_created = 0
        
        with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            
            self.stdout.write(f'Processing states from {file_path}...')
            
            with transaction.atomic():
                for row in reader:
                    try:
                        # Extract data from CSV
                        codigo_uf = row['codigo_uf'].strip()
                        uf = row['uf'].strip()
                        nome = row['nome'].strip()
                        latitude = Decimal(row['latitude'].strip()) if row['latitude'].strip() else None
                        longitude = Decimal(row['longitude'].strip()) if row['longitude'].strip() else None
                        regiao_name = row['regiao'].strip() if row['regiao'].strip() else None
                        
                        # Get or create region
                        region = None
                        if regiao_name:
                            region = self.get_or_create_region(regiao_name, dry_run)
                        
                        if not dry_run:
                            # Find existing state by numeric code
                            try:
                                state = State.objects.get(code=codigo_uf)
                                # Update existing state with new data
                                state.abbreviation = uf
                                state.latitude = latitude
                                state.longitude = longitude
                                state.regiao = regiao_name
                                state.region = region
                                state.save()
                                states_created += 1
                                self.stdout.write(f'Updated state: {nome} ({uf}) - {regiao_name}')
                            except State.DoesNotExist:
                                self.stdout.write(f'State with code {codigo_uf} not found, skipping {nome}')
                        else:
                            # Check if state exists
                            try:
                                state = State.objects.get(code=codigo_uf)
                                states_created += 1
                                self.stdout.write(f'Would update state: {nome} ({uf}) - {regiao_name}')
                            except State.DoesNotExist:
                                self.stdout.write(f'State with code {codigo_uf} not found, would skip {nome}')
                    
                    except Exception as e:
                        logger.error(f'Error processing state: {row}, Error: {str(e)}')
                        self.stdout.write(
                            self.style.ERROR(f'Error processing state {row.get("nome", "Unknown")}: {str(e)}')
                        )
                        continue
            
            self.stdout.write(
                self.style.SUCCESS(f'Import summary: {states_created} states processed')
            )
            
            return states_created
