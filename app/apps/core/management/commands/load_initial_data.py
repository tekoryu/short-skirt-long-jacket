"""
This management command is responsible for loading initial fixture data in the correct order.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Load initial data fixtures in the correct order'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-cities',
            action='store_true',
            help='Skip loading cities data (useful if only updating auth data)',
        )
        parser.add_argument(
            '--skip-auth',
            action='store_true',
            help='Skip loading auth data (useful if only updating cities data)',
        )

    def handle(self, *args, **options):
        skip_cities = options['skip_cities']
        skip_auth = options['skip_auth']

        self.stdout.write(self.style.SUCCESS('Starting initial data load...'))

        # Load cities data first (has foreign key dependencies within itself)
        if not skip_cities:
            self.stdout.write('Loading cities data (regions, states, municipalities)...')
            try:
                call_command('loaddata', 'cities_initial_data.json', verbosity=1)
                self.stdout.write(self.style.SUCCESS('✓ Cities data loaded successfully'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Failed to load cities data: {e}'))
                return

        # Load auth data (groups, permissions)
        if not skip_auth:
            self.stdout.write('Loading auth data (groups, permissions)...')
            try:
                call_command('loaddata', 'auth_initial_data.json', verbosity=1)
                self.stdout.write(self.style.SUCCESS('✓ Auth data loaded successfully'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Failed to load auth data: {e}'))
                return

        self.stdout.write(self.style.SUCCESS('\n✓ All initial data loaded successfully!'))
        self.stdout.write(self.style.WARNING(
            '\nNote: This does not create user accounts. '
            'Superuser creation is handled separately via environment variables.'
        ))

