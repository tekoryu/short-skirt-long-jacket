"""
This class is responsible for importing SEAF category classifications for municipalities from a CSV file.
"""
import csv
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.cities.models import Municipality

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import SEAF category classification data for municipalities from CSV file'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='/app/data/SEAF/tbl_ClassificacaoMunicípios2025_SEAF(in).csv',
            help='Path to the CSV file (default: /app/data/SEAF/tbl_ClassificacaoMunicípios2025_SEAF(in).csv)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        file_path = options['file']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting SEAF data import at {start_time}')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No data will be imported')
            )
        
        try:
            # Import data
            stats = self.import_data(file_path, dry_run)
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nImport completed successfully!\n'
                    f'Total records in CSV: {stats["total"]}\n'
                    f'Municipalities matched: {stats["matched"]}\n'
                    f'Municipalities updated: {stats["updated"]}\n'
                    f'Municipalities not found: {stats["not_found"]}\n'
                    f'Skipped (empty category): {stats["skipped"]}\n'
                    f'Duration: {duration:.2f} seconds'
                )
            )
            
            if stats["not_found_codes"]:
                self.stdout.write(
                    self.style.WARNING(
                        f'\nMunicipalities not found in database ({len(stats["not_found_codes"])}):'
                    )
                )
                for code, name in stats["not_found_codes"][:10]:
                    self.stdout.write(f'  - {code}: {name}')
                if len(stats["not_found_codes"]) > 10:
                    self.stdout.write(f'  ... and {len(stats["not_found_codes"]) - 10} more')
            
        except FileNotFoundError:
            raise CommandError(f'CSV file not found: {file_path}')
        except Exception as e:
            logger.error(f'Error during import: {str(e)}')
            raise CommandError(f'Import failed: {str(e)}')
    
    def import_data(self, file_path, dry_run):
        """Import SEAF category data from CSV file"""
        stats = {
            'total': 0,
            'matched': 0,
            'updated': 0,
            'not_found': 0,
            'skipped': 0,
            'not_found_codes': []
        }
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # The CSV uses semicolon as delimiter
            reader = csv.DictReader(csvfile, delimiter=';')
            
            self.stdout.write('Processing records...')
            
            with transaction.atomic():
                for row in reader:
                    stats['total'] += 1
                    
                    try:
                        # Extract data from CSV
                        ibge_code = row['COD IBGE Completo'].strip()
                        municipality_name = row['Nome_Município'].strip()
                        categoria = row['CATEGORIA'].strip()
                        
                        # Skip if category is empty
                        if not categoria:
                            stats['skipped'] += 1
                            continue
                        
                        # Convert category to integer
                        try:
                            seaf_category = int(categoria)
                        except ValueError:
                            logger.warning(f'Invalid CATEGORIA value for {municipality_name} ({ibge_code}): {categoria}')
                            stats['skipped'] += 1
                            continue
                        
                        # Find municipality by IBGE code
                        try:
                            municipality = Municipality.objects.get(code=ibge_code)
                            stats['matched'] += 1
                            
                            # Update the SEAF category
                            if not dry_run:
                                municipality.seaf_category = seaf_category
                                municipality.save(update_fields=['seaf_category'])
                                stats['updated'] += 1
                            else:
                                stats['updated'] += 1
                            
                            # Progress update every 500 records
                            if stats['total'] % 500 == 0:
                                self.stdout.write(
                                    f'Processed {stats["total"]} records... '
                                    f'(matched: {stats["matched"]}, not found: {stats["not_found"]})'
                                )
                        
                        except Municipality.DoesNotExist:
                            stats['not_found'] += 1
                            stats['not_found_codes'].append((ibge_code, municipality_name))
                            logger.warning(f'Municipality not found: {municipality_name} ({ibge_code})')
                    
                    except Exception as e:
                        logger.error(f'Error processing row: {row}, Error: {str(e)}')
                        self.stdout.write(
                            self.style.ERROR(f'Error processing municipality {row.get("Nome_Município", "Unknown")}: {str(e)}')
                        )
                        continue
        
        return stats



