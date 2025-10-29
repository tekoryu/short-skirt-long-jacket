import csv
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.cities.models import Municipality

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import additional municipality data from municipios.csv file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='/app/data/municipios-brasileiros/csv/municipios.csv',
            help='Path to the CSV file (default: /app/data/municipios-brasileiros/csv/municipios.csv)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Number of records to process in each batch (default: 500)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating'
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        file_path = options['file']
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.SUCCESS(f'Starting municipios data import at {start_time}')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No data will be updated')
            )

        try:
            stats = self.import_data(file_path, batch_size, dry_run)

            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()

            self.stdout.write(
                self.style.SUCCESS(
                    f'\nImport completed successfully!\n'
                    f'Total rows in CSV: {stats["total"]}\n'
                    f'Municipalities updated: {stats["updated"]}\n'
                    f'Municipalities not found: {stats["not_found"]}\n'
                    f'Name mismatches: {stats["name_mismatch"]}\n'
                    f'Errors: {stats["errors"]}\n'
                    f'Duration: {duration:.2f} seconds'
                )
            )

        except FileNotFoundError:
            raise CommandError(f'CSV file not found: {file_path}')
        except Exception as e:
            logger.error(f'Error during import: {str(e)}')
            raise CommandError(f'Import failed: {str(e)}')

    def import_data(self, file_path, batch_size, dry_run):
        """Import data from CSV file"""
        stats = {
            'total': 0,
            'updated': 0,
            'not_found': 0,
            'name_mismatch': 0,
            'errors': 0
        }

        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            # Count total rows
            total_rows = sum(1 for _ in reader)
            csvfile.seek(0)
            reader = csv.DictReader(csvfile)

            self.stdout.write(f'Processing {total_rows} records...\n')

            batch = []
            processed = 0

            for row in reader:
                batch.append(row)
                processed += 1
                stats['total'] += 1

                if len(batch) >= batch_size:
                    batch_stats = self.process_batch(batch, dry_run)
                    stats['updated'] += batch_stats['updated']
                    stats['not_found'] += batch_stats['not_found']
                    stats['name_mismatch'] += batch_stats['name_mismatch']
                    stats['errors'] += batch_stats['errors']
                    batch = []

                    # Progress update
                    if processed % (batch_size * 2) == 0:
                        self.stdout.write(
                            f'Processed {processed}/{total_rows} records... '
                            f'(Updated: {stats["updated"]}, Not found: {stats["not_found"]}, '
                            f'Name mismatches: {stats["name_mismatch"]}, Errors: {stats["errors"]})'
                        )

            # Process remaining records
            if batch:
                batch_stats = self.process_batch(batch, dry_run)
                stats['updated'] += batch_stats['updated']
                stats['not_found'] += batch_stats['not_found']
                stats['name_mismatch'] += batch_stats['name_mismatch']
                stats['errors'] += batch_stats['errors']

            return stats

    def process_batch(self, batch, dry_run):
        """Process a batch of records"""
        stats = {
            'updated': 0,
            'not_found': 0,
            'name_mismatch': 0,
            'errors': 0
        }

        with transaction.atomic():
            for row in batch:
                try:
                    # Get data from CSV
                    codigo_ibge = row['codigo_ibge'].strip()
                    nome = row['nome'].strip()
                    latitude = row['latitude'].strip() if row['latitude'] else None
                    longitude = row['longitude'].strip() if row['longitude'] else None
                    capital = row['capital'].strip() == '1'
                    siafi_id = row['siafi_id'].strip() if row['siafi_id'] else None
                    ddd = row['ddd'].strip() if row['ddd'] else None
                    fuso_horario = row['fuso_horario'].strip() if row['fuso_horario'] else None

                    # Try to find the municipality by code
                    try:
                        municipality = Municipality.objects.get(code=codigo_ibge)

                        # Log if the name differs (but continue updating)
                        if municipality.name != nome:
                            logger.info(
                                f'Name difference for code {codigo_ibge}: '
                                f'DB has "{municipality.name}", CSV has "{nome}" - updating anyway'
                            )
                            stats['name_mismatch'] += 1

                        # Update the municipality data
                        if not dry_run:
                            updated = False
                            if latitude and (not municipality.latitude or str(municipality.latitude) != latitude):
                                municipality.latitude = latitude
                                updated = True
                            if longitude and (not municipality.longitude or str(municipality.longitude) != longitude):
                                municipality.longitude = longitude
                                updated = True
                            if municipality.is_capital != capital:
                                municipality.is_capital = capital
                                updated = True
                            if siafi_id and municipality.siafi_id != siafi_id:
                                municipality.siafi_id = siafi_id
                                updated = True
                            if ddd and municipality.area_code != ddd:
                                municipality.area_code = ddd
                                updated = True
                            if fuso_horario and municipality.timezone != fuso_horario:
                                municipality.timezone = fuso_horario
                                updated = True

                            if updated:
                                municipality.save()
                                stats['updated'] += 1
                        else:
                            # In dry-run mode, just count as updated
                            stats['updated'] += 1

                    except Municipality.DoesNotExist:
                        logger.warning(f'Municipality not found with code: {codigo_ibge} (name: {nome})')
                        stats['not_found'] += 1

                except Exception as e:
                    logger.error(f'Error processing row: {row}, Error: {str(e)}')
                    self.stdout.write(
                        self.style.ERROR(f'Error processing municipality {row.get("nome", "Unknown")}: {str(e)}')
                    )
                    stats['errors'] += 1
                    continue

        return stats
