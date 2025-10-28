import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.cities.models import State, IntermediateRegion, ImmediateRegion, Municipality

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clear all IBGE geographic data from the database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all data (required for safety)'
        )
        parser.add_argument(
            '--stats-only',
            action='store_true',
            help='Only show current data statistics without deleting'
        )
    
    def handle(self, *args, **options):
        confirm = options['confirm']
        stats_only = options['stats_only']
        
        # Get current data counts
        stats = self.get_data_stats()
        
        self.stdout.write(
            self.style.WARNING(
                f'Current data in database:\n'
                f'States: {stats["states"]}\n'
                f'Intermediate Regions: {stats["intermediate_regions"]}\n'
                f'Immediate Regions: {stats["immediate_regions"]}\n'
                f'Municipalities: {stats["municipalities"]}'
            )
        )
        
        if stats_only:
            self.stdout.write(
                self.style.SUCCESS('Stats-only mode - no data deleted')
            )
            return
        
        if not confirm:
            self.stdout.write(
                self.style.ERROR(
                    'This will permanently delete ALL geographic data!\n'
                    'Use --confirm flag to proceed with deletion.'
                )
            )
            return
        
        try:
            with transaction.atomic():
                self.clear_all_data()
            
            # Verify deletion
            final_stats = self.get_data_stats()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Data cleared successfully!\n'
                    f'Remaining records:\n'
                    f'States: {final_stats["states"]}\n'
                    f'Intermediate Regions: {final_stats["intermediate_regions"]}\n'
                    f'Immediate Regions: {final_stats["immediate_regions"]}\n'
                    f'Municipalities: {final_stats["municipalities"]}'
                )
            )
            
        except Exception as e:
            logger.error(f'Error during data clearing: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Failed to clear data: {str(e)}')
            )
            raise
    
    def get_data_stats(self):
        """Get current data statistics"""
        return {
            'states': State.objects.count(),
            'intermediate_regions': IntermediateRegion.objects.count(),
            'immediate_regions': ImmediateRegion.objects.count(),
            'municipalities': Municipality.objects.count(),
        }
    
    def clear_all_data(self):
        """Clear all geographic data in correct order (respecting foreign keys)"""
        self.stdout.write('Clearing municipalities...')
        municipalities_deleted = Municipality.objects.count()
        Municipality.objects.all().delete()
        self.stdout.write(f'Deleted {municipalities_deleted} municipalities')
        
        self.stdout.write('Clearing immediate regions...')
        immediate_regions_deleted = ImmediateRegion.objects.count()
        ImmediateRegion.objects.all().delete()
        self.stdout.write(f'Deleted {immediate_regions_deleted} immediate regions')
        
        self.stdout.write('Clearing intermediate regions...')
        intermediate_regions_deleted = IntermediateRegion.objects.count()
        IntermediateRegion.objects.all().delete()
        self.stdout.write(f'Deleted {intermediate_regions_deleted} intermediate regions')
        
        self.stdout.write('Clearing states...')
        states_deleted = State.objects.count()
        State.objects.all().delete()
        self.stdout.write(f'Deleted {states_deleted} states')
