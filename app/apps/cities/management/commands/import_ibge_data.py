import csv
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.cities.models import State, IntermediateRegion, ImmediateRegion, Municipality

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import IBGE municipalities data from CSV file'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='/app/data/ibge/RELATORIO_DTB_BRASIL_2024_MUNICIPIOS.csv',
            help='Path to the CSV file (default: /app/data/ibge/RELATORIO_DTB_BRASIL_2024_MUNICIPIOS.csv)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process in each batch (default: 1000)'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing data before importing'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        file_path = options['file']
        batch_size = options['batch_size']
        clear_existing = options['clear_existing']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting IBGE data import at {start_time}')
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
            imported_count = self.import_data(file_path, batch_size, dry_run)
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Import completed successfully!\n'
                    f'Records processed: {imported_count}\n'
                    f'Duration: {duration:.2f} seconds'
                )
            )
            
        except FileNotFoundError:
            raise CommandError(f'CSV file not found: {file_path}')
        except Exception as e:
            logger.error(f'Error during import: {str(e)}')
            raise CommandError(f'Import failed: {str(e)}')
    
    def clear_existing_data(self):
        """Clear all existing geographic data"""
        self.stdout.write('Clearing existing data...')
        
        Municipality.objects.all().delete()
        ImmediateRegion.objects.all().delete()
        IntermediateRegion.objects.all().delete()
        State.objects.all().delete()
        
        self.stdout.write(
            self.style.SUCCESS('Existing data cleared successfully')
        )
    
    def import_data(self, file_path, batch_size, dry_run):
        """Import data from CSV file"""
        states_created = {}
        intermediate_regions_created = {}
        immediate_regions_created = {}
        municipalities_created = 0
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            total_rows = sum(1 for _ in reader)
            csvfile.seek(0)
            reader = csv.DictReader(csvfile)
            
            self.stdout.write(f'Processing {total_rows} records...')
            
            batch = []
            processed = 0
            
            for row in reader:
                batch.append(row)
                processed += 1
                
                if len(batch) >= batch_size:
                    batch_created = self.process_batch(
                        batch, states_created, intermediate_regions_created, 
                        immediate_regions_created, dry_run
                    )
                    municipalities_created += batch_created
                    batch = []
                    
                    # Progress update
                    if processed % (batch_size * 5) == 0:
                        self.stdout.write(f'Processed {processed}/{total_rows} records...')
            
            # Process remaining records
            if batch:
                batch_created = self.process_batch(
                    batch, states_created, intermediate_regions_created, 
                    immediate_regions_created, dry_run
                )
                municipalities_created += batch_created
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Import summary:\n'
                    f'States: {len(states_created)}\n'
                    f'Intermediate Regions: {len(intermediate_regions_created)}\n'
                    f'Immediate Regions: {len(immediate_regions_created)}\n'
                    f'Municipalities: {municipalities_created}'
                )
            )
            
            return municipalities_created
    
    def process_batch(self, batch, states_created, intermediate_regions_created, 
                     immediate_regions_created, dry_run):
        """Process a batch of records"""
        municipalities_created = 0
        
        with transaction.atomic():
            for row in batch:
                try:
                    # Create or get State
                    state_code = row['UF'].strip()
                    state_name = row['Nome_UF'].strip()
                    
                    if state_code not in states_created:
                        if not dry_run:
                            state, created = State.objects.get_or_create(
                                code=state_code,
                                defaults={'name': state_name}
                            )
                        else:
                            state = None
                            created = state_code not in states_created
                        
                        states_created[state_code] = {
                            'obj': state,
                            'name': state_name,
                            'created': created
                        }
                    
                    # Create or get Intermediate Region
                    intermediate_code = row['Região Geográfica Intermediária'].strip()
                    intermediate_name = row['Nome Região Geográfica Intermediária'].strip()
                    
                    if intermediate_code not in intermediate_regions_created:
                        if not dry_run:
                            intermediate_region, created = IntermediateRegion.objects.get_or_create(
                                code=intermediate_code,
                                defaults={
                                    'name': intermediate_name,
                                    'state': states_created[state_code]['obj']
                                }
                            )
                        else:
                            intermediate_region = None
                            created = intermediate_code not in intermediate_regions_created
                        
                        intermediate_regions_created[intermediate_code] = {
                            'obj': intermediate_region,
                            'name': intermediate_name,
                            'state_code': state_code,
                            'created': created
                        }
                    
                    # Create or get Immediate Region
                    immediate_code = row['Região Geográfica Imediata'].strip()
                    immediate_name = row['Nome Região Geográfica Imediata'].strip()
                    
                    if immediate_code not in immediate_regions_created:
                        if not dry_run:
                            immediate_region, created = ImmediateRegion.objects.get_or_create(
                                code=immediate_code,
                                defaults={
                                    'name': immediate_name,
                                    'intermediate_region': intermediate_regions_created[intermediate_code]['obj']
                                }
                            )
                        else:
                            immediate_region = None
                            created = immediate_code not in immediate_regions_created
                        
                        immediate_regions_created[immediate_code] = {
                            'obj': immediate_region,
                            'name': immediate_name,
                            'intermediate_code': intermediate_code,
                            'created': created
                        }
                    
                    # Create Municipality
                    municipality_code = row['Código Município Completo'].strip()
                    municipality_name = row['Nome_Município'].strip()
                    
                    if not dry_run:
                        municipality, created = Municipality.objects.get_or_create(
                            code=municipality_code,
                            defaults={
                                'name': municipality_name,
                                'immediate_region': immediate_regions_created[immediate_code]['obj']
                            }
                        )
                        if created:
                            municipalities_created += 1
                    else:
                        municipalities_created += 1
                    
                except Exception as e:
                    logger.error(f'Error processing row: {row}, Error: {str(e)}')
                    self.stdout.write(
                        self.style.ERROR(f'Error processing municipality {row.get("Nome_Município", "Unknown")}: {str(e)}')
                    )
                    continue
        
        return municipalities_created
