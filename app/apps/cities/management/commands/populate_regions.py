import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.cities.models import Region, State

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate Brazilian regions and migrate existing state data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it'
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting region population at {start_time}')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No data will be modified')
            )
        
        try:
            with transaction.atomic():
                # Create regions
                regions_data = [
                    {'code': 'N', 'name': 'Norte'},
                    {'code': 'NE', 'name': 'Nordeste'},
                    {'code': 'SE', 'name': 'Sudeste'},
                    {'code': 'S', 'name': 'Sul'},
                    {'code': 'CO', 'name': 'Centro-Oeste'},
                ]
                
                regions_created = 0
                for region_data in regions_data:
                    if not dry_run:
                        region, created = Region.objects.get_or_create(
                            code=region_data['code'],
                            defaults={'name': region_data['name']}
                        )
                        if created:
                            regions_created += 1
                            self.stdout.write(f'Created region: {region.name} ({region.code})')
                        else:
                            self.stdout.write(f'Region already exists: {region.name} ({region.code})')
                    else:
                        try:
                            region = Region.objects.get(code=region_data['code'])
                            self.stdout.write(f'Would skip existing region: {region.name} ({region.code})')
                        except Region.DoesNotExist:
                            regions_created += 1
                            self.stdout.write(f'Would create region: {region_data["name"]} ({region_data["code"]})')
                
                # Migrate existing states from regiao CharField to region ForeignKey
                states_migrated = 0
                states_without_region = State.objects.filter(regiao__isnull=False, region__isnull=True)
                
                self.stdout.write(f'\nMigrating {states_without_region.count()} states with regiao but no region FK...')
                
                for state in states_without_region:
                    try:
                        if not dry_run:
                            region = Region.objects.get(name=state.regiao)
                            state.region = region
                            state.save()
                            states_migrated += 1
                            self.stdout.write(f'Migrated state: {state.name} -> {region.name}')
                        else:
                            try:
                                region = Region.objects.get(name=state.regiao)
                                states_migrated += 1
                                self.stdout.write(f'Would migrate state: {state.name} -> {region.name}')
                            except Region.DoesNotExist:
                                self.stdout.write(
                                    self.style.WARNING(f'Would skip state {state.name}: region "{state.regiao}" not found')
                                )
                    except Region.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Region not found for state {state.name}: {state.regiao}')
                        )
                    except Exception as e:
                        logger.error(f'Error migrating state {state.name}: {str(e)}')
                        self.stdout.write(
                            self.style.ERROR(f'Error migrating state {state.name}: {str(e)}')
                        )
                
                end_time = timezone.now()
                duration = (end_time - start_time).total_seconds()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nPopulation completed successfully!\n'
                        f'Regions created: {regions_created}\n'
                        f'States migrated: {states_migrated}\n'
                        f'Duration: {duration:.2f} seconds'
                    )
                )
        
        except Exception as e:
            logger.error(f'Error during population: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Population failed: {str(e)}')
            )
            raise


