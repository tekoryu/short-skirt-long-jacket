"""
This module is responsible for setting up region-scoped permission groups.
"""
import logging
from typing import List, Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.auth.models import GroupResourcePermission, PermissionLog, ResourcePermission
from apps.cities.models import Region

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    """
    This command is responsible for creating region-scoped permission groups using GroupResourcePermission.
    """

    help = "Create or refresh region-scoped permission groups"

    def add_arguments(self, parser):
        parser.add_argument(
            "--resource",
            default="cities.municipality",
            help="Resource name for permissions (default: cities.municipality)",
        )
        parser.add_argument(
            "--permissions",
            default="view,change",
            help="Comma-separated permission types (default: view,change)",
        )
        parser.add_argument(
            "--group-prefix",
            default="Region - ",
            help="Prefix for group names (default: 'Region - ')",
        )
        parser.add_argument(
            "--global-group",
            default="Cities - Global Access",
            help="Name for global access group (default: 'Cities - Global Access')",
        )
        parser.add_argument(
            "--create-global",
            action="store_true",
            help="Also create a global access group (no region restriction)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without making changes",
        )

    def handle(self, *args, **options):
        resource = options["resource"]
        permission_types = self._parse_permissions(options["permissions"])
        group_prefix = options["group_prefix"]
        global_group_name = options["global_group"]
        create_global = options["create_global"]
        dry_run = options["dry_run"]

        if not permission_types:
            raise CommandError("At least one permission type must be provided.")

        regions = list(Region.objects.order_by("code"))
        if not regions:
            raise CommandError("No regions found. Run populate_regions first.")

        permissions = self._fetch_permissions(resource, permission_types)

        if dry_run:
            self._dry_run(regions, permissions, group_prefix, global_group_name, create_global)
            return

        with transaction.atomic():
            summary = self._create_region_groups(regions, permissions, group_prefix)
            
            if create_global:
                summary["global_created"] = self._create_global_group(
                    global_group_name, permissions
                )

        self._print_summary(summary)

    def _parse_permissions(self, permissions_param: str) -> List[str]:
        return [p.strip() for p in permissions_param.split(",") if p.strip()]

    def _fetch_permissions(self, resource: str, permission_types: List[str]) -> dict:
        permissions = {}
        missing = []
        
        for perm_type in permission_types:
            try:
                permissions[perm_type] = ResourcePermission.objects.get(
                    resource_name=resource, permission_type=perm_type
                )
            except ResourcePermission.DoesNotExist:
                missing.append(perm_type)

        if missing:
            raise CommandError(
                f"Missing ResourcePermission for types: {', '.join(missing)} "
                f"and resource: {resource}. Create them first."
            )
        
        return permissions

    def _create_region_groups(self, regions, permissions, group_prefix) -> dict:
        summary = {"groups_created": 0, "permissions_linked": 0}
        
        for region in regions:
            group_name = f"{group_prefix}{region.name}"
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                summary["groups_created"] += 1
                self.stdout.write(self.style.SUCCESS(f"✓ Created group: {group_name}"))
            else:
                self.stdout.write(f"  Exists: {group_name}")
            
            # Link permissions with region scope
            for perm_type, permission in permissions.items():
                grp, link_created = GroupResourcePermission.objects.get_or_create(
                    group=group,
                    resource_permission=permission,
                    region=region,
                )
                if link_created:
                    summary["permissions_linked"] += 1
                    self._log_creation(group, permission, region)
        
        return summary

    def _create_global_group(self, group_name: str, permissions: dict) -> int:
        group, created = Group.objects.get_or_create(name=group_name)
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Created global group: {group_name}"))
        else:
            self.stdout.write(f"  Global group exists: {group_name}")
        
        count = 0
        for perm_type, permission in permissions.items():
            grp, link_created = GroupResourcePermission.objects.get_or_create(
                group=group,
                resource_permission=permission,
                region=None,  # Global access
            )
            if link_created:
                count += 1
                self._log_creation(group, permission, None)
        
        return count

    def _log_creation(self, group: Group, permission: ResourcePermission, region: Optional[Region]):
        system_user = User.objects.filter(is_superuser=True).order_by("id").first()
        if not system_user:
            logger.warning("No superuser found for logging.")
            return
        
        region_str = region.name if region else "GLOBAL"
        PermissionLog.objects.create(
            user=system_user,
            action="group_added",
            resource=permission.resource_name,
            details=f"{group.name} <= {permission.codename} (region={region_str})",
        )

    def _dry_run(self, regions, permissions, group_prefix, global_group_name, create_global):
        self.stdout.write(self.style.WARNING("\n=== DRY RUN ===\n"))
        
        self.stdout.write("Would create region groups:")
        for region in regions:
            group_name = f"{group_prefix}{region.name}"
            self.stdout.write(f"  - {group_name}")
            for perm_type in permissions:
                self.stdout.write(f"      + {perm_type} (region={region.name})")
        
        if create_global:
            self.stdout.write(f"\nWould create global group: {global_group_name}")
            for perm_type in permissions:
                self.stdout.write(f"      + {perm_type} (region=GLOBAL)")

    def _print_summary(self, summary: dict):
        self.stdout.write(self.style.SUCCESS("\n=== Summary ==="))
        self.stdout.write(f"  Groups created: {summary.get('groups_created', 0)}")
        self.stdout.write(f"  Permission links created: {summary.get('permissions_linked', 0)}")
        if "global_created" in summary:
            self.stdout.write(f"  Global permissions linked: {summary['global_created']}")

