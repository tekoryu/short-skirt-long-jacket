import logging
from typing import Dict, List

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.auth.models import GroupResourcePermission, PermissionLog, ResourcePermission
from apps.cities.constants import GLOBAL_VIEW_GROUP, REGION_GROUP_PREFIX
from apps.cities.models import Region

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    """
    This command is responsible for creating region-scoped Django groups and wiring them to ResourcePermission entries.
    """

    help = "Create or refresh region control groups and attach resource permissions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--resource",
            default="cities.city",
            help="Resource name used by ResourcePermission entries (default: cities.city)",
        )
        parser.add_argument(
            "--permissions",
            default="view,download,change",
            help="Comma separated permission types (default: view,download,change)",
        )
        parser.add_argument(
            "--auto-assign-superusers",
            action="store_true",
            help="Also add verified superusers to every region group",
        )

    def handle(self, *args, **options):
        resource = options["resource"]
        permission_types = self._clean_permission_types(options["permissions"])
        auto_assign = options["auto_assign_superusers"]

        if not permission_types:
            raise CommandError("At least one permission type must be provided.")

        regions = list(Region.objects.order_by("code"))
        if not regions:
            raise CommandError("No regions found. Run populate_regions before this command.")

        permissions = self._fetch_permissions(resource, permission_types)

        with transaction.atomic():
            summary = {
                "groups_created": 0,
                "group_permissions_created": 0,
                "global_group_permissions_created": 0,
            }
            for region in regions:
                group_name = f"{REGION_GROUP_PREFIX}{region.name}"
                group, created = Group.objects.get_or_create(name=group_name)
                if created:
                    summary["groups_created"] += 1
                    self.stdout.write(self.style.SUCCESS(f"✓ Created group {group_name}"))
                else:
                    self.stdout.write(self.style.WARNING(f"• Group exists {group_name}"))

                summary["group_permissions_created"] += self._assign_permissions(group, permissions)

                if auto_assign:
                    self._auto_assign_superusers(group)

            summary["global_group_permissions_created"] = self._ensure_global_view_group(permissions)

        self.stdout.write(self.style.SUCCESS("\nSummary"))
        self.stdout.write(f"  Groups created: {summary['groups_created']}")
        self.stdout.write(f"  Region permission links created: {summary['group_permissions_created']}")
        self.stdout.write(
            f"  Global view permission links created: {summary['global_group_permissions_created']}"
        )

    def _clean_permission_types(self, permissions_param: str) -> List[str]:
        return [perm.strip() for perm in permissions_param.split(",") if perm.strip()]

    def _fetch_permissions(self, resource: str, permission_types: List[str]) -> Dict[str, ResourcePermission]:
        permissions: Dict[str, ResourcePermission] = {}
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
                f"Missing ResourcePermission entries for types {', '.join(missing)} and resource {resource}."
            )
        return permissions

    def _assign_permissions(self, group: Group, permissions: Dict[str, ResourcePermission]) -> int:
        created = 0
        for permission in permissions.values():
            group_perm, is_new = GroupResourcePermission.objects.get_or_create(
                group=group, resource_permission=permission
            )
            if is_new:
                created += 1
                self._log_assignment(group, permission)
        return created

    def _ensure_global_view_group(self, permissions: Dict[str, ResourcePermission]) -> int:
        group, _ = Group.objects.get_or_create(name=GLOBAL_VIEW_GROUP)
        view_permission = permissions.get("view")
        if not view_permission:
            self.stdout.write(
                self.style.WARNING(
                    "⚠ No 'view' permission in selection; Brasil group will not receive any permission."
                )
            )
            return 0
        group_perm, created = GroupResourcePermission.objects.get_or_create(
            group=group, resource_permission=view_permission
        )
        if created:
            self._log_assignment(group, view_permission)
            self.stdout.write(self.style.SUCCESS(f"✓ Ensured global view group {GLOBAL_VIEW_GROUP}"))
            return 1
        self.stdout.write(self.style.WARNING(f"• Global view group {GLOBAL_VIEW_GROUP} already wired"))
        return 0

    def _auto_assign_superusers(self, group: Group) -> None:
        superusers = User.objects.filter(is_superuser=True, is_active=True, is_verified=True)
        for user in superusers:
            if not user.groups.filter(pk=group.pk).exists():
                user.groups.add(group)
                self.stdout.write(f"  ↪ Added superuser {user.email} to {group.name}")

    def _log_assignment(self, group: Group, permission: ResourcePermission) -> None:
        system_user = User.objects.filter(is_superuser=True).order_by("id").first()
        if not system_user:
            logger.warning(
                "Skipping PermissionLog entry for group %s because no superuser exists.", group.name
            )
            return
        PermissionLog.objects.create(
            user=system_user,
            action="group_added",
            resource=permission.resource_name,
            details=f"{group.name} <= {permission.codename} (create_region_groups)",
        )

