from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import PermissionLog, UserPermission, UserGroup

User = get_user_model()


@receiver(post_save, sender=User)
def log_user_creation(sender, instance, created, **kwargs):
    """
    Log when a new user is created.
    """
    if created:
        PermissionLog.objects.create(
            user=instance,
            action='granted',
            resource='user.creation',
            details='User account created'
        )


@receiver(post_save, sender=UserPermission)
def log_permission_granted(sender, instance, created, **kwargs):
    """
    Log when a permission is granted to a user.
    """
    if created:
        PermissionLog.objects.create(
            user=instance.user,
            action='granted',
            resource=f"{instance.resource_permission.resource_name}.{instance.resource_permission.permission_type}",
            details=f"Permission granted by {instance.granted_by.email if instance.granted_by else 'System'}"
        )


@receiver(pre_delete, sender=UserPermission)
def log_permission_revoked(sender, instance, **kwargs):
    """
    Log when a permission is revoked from a user.
    """
    PermissionLog.objects.create(
        user=instance.user,
        action='revoked',
        resource=f"{instance.resource_permission.resource_name}.{instance.resource_permission.permission_type}",
        details=f"Permission revoked"
    )


@receiver(post_save, sender=UserGroup)
def log_group_assignment(sender, instance, created, **kwargs):
    """
    Log when a user is added to a group.
    """
    if created:
        PermissionLog.objects.create(
            user=instance.user,
            action='group_added',
            resource=instance.group.name,
            details=f"Added to group by {instance.added_by.email if instance.added_by else 'System'}"
        )


@receiver(pre_delete, sender=UserGroup)
def log_group_removal(sender, instance, **kwargs):
    """
    Log when a user is removed from a group.
    """
    PermissionLog.objects.create(
        user=instance.user,
        action='group_removed',
        resource=instance.group.name,
        details=f"Removed from group"
    )
