from django.core.management.base import BaseCommand
from django.db import transaction
from apps.auth.models import (
    User, PermissionGroup, ResourcePermission,
    GroupPermission, UserGroup
)


class Command(BaseCommand):
    """
    This command is responsible for creating an administrator group with full access to all resources.
    """
    help = 'Creates an administrator group with full access to all resources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--group-name',
            type=str,
            default='Administrators',
            help='Name of the administrator group (default: Administrators)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        group_name = options['group_name']

        # Create or get the administrator group
        group, created = PermissionGroup.objects.get_or_create(
            name=group_name,
            defaults={
                'description': 'Full access to all system resources',
                'is_active': True
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created group: {group_name}'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠ Group already exists: {group_name}'))

        # Define all resources and permission types
        resources = [
            {
                'resource_name': 'cities.city',
                'permissions': [
                    {'type': 'view', 'name': 'View Cities', 'codename': 'view_cities_city', 'description': 'Permission to view cities list'},
                    {'type': 'download', 'name': 'Download Cities', 'codename': 'download_cities_city', 'description': 'Permission to download cities data'},
                    {'type': 'edit', 'name': 'Edit Cities', 'codename': 'edit_cities_city', 'description': 'Permission to edit cities data'},
                ]
            },
            # Add more resources here as needed
        ]

        permissions_created = 0
        permissions_existing = 0
        group_perms_created = 0

        for resource in resources:
            resource_name = resource['resource_name']
            
            for perm_def in resource['permissions']:
                # Create or get resource permission
                resource_perm, perm_created = ResourcePermission.objects.get_or_create(
                    resource_name=resource_name,
                    permission_type=perm_def['type'],
                    defaults={
                        'name': perm_def['name'],
                        'codename': perm_def['codename'],
                        'description': perm_def['description'],
                        'is_active': True
                    }
                )

                if perm_created:
                    permissions_created += 1
                    self.stdout.write(f'  ✓ Created permission: {perm_def["name"]} ({resource_name}/{perm_def["type"]})')
                else:
                    permissions_existing += 1
                    self.stdout.write(f'  - Permission exists: {perm_def["name"]}')

                # Assign permission to group
                group_perm, gp_created = GroupPermission.objects.get_or_create(
                    group=group,
                    resource_permission=resource_perm
                )

                if gp_created:
                    group_perms_created += 1

        self.stdout.write(self.style.SUCCESS(f'\n✓ Summary:'))
        self.stdout.write(f'  - Permissions created: {permissions_created}')
        self.stdout.write(f'  - Permissions already existed: {permissions_existing}')
        self.stdout.write(f'  - Group permissions assigned: {group_perms_created}')

        # Add all superusers to the group
        superusers = User.objects.filter(is_superuser=True, is_active=True)
        users_added = 0

        for user in superusers:
            user_group, ug_created = UserGroup.objects.get_or_create(
                user=user,
                group=group,
                defaults={
                    'is_active': True,
                    'added_by': user
                }
            )

            if ug_created:
                users_added += 1
                self.stdout.write(f'  ✓ Added user to group: {user.username}')

        if users_added > 0:
            self.stdout.write(self.style.SUCCESS(f'\n✓ Added {users_added} superuser(s) to {group_name} group'))
        else:
            self.stdout.write(self.style.WARNING(f'\n⚠ No new users added to group'))

        self.stdout.write(self.style.SUCCESS(f'\n✓ Administrator group setup complete!'))

