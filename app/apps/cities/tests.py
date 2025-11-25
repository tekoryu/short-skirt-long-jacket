"""
This module is responsible for testing region-scoped permission functionality.
"""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import RequestFactory, TestCase

from apps.auth.decorators import check_resource_permission, get_user_permitted_regions
from apps.auth.models import GroupResourcePermission, ResourcePermission
from apps.cities.admin import MunicipalityAdmin, StateAdmin
from apps.cities.models import (
    ImmediateRegion,
    IntermediateRegion,
    Municipality,
    Region,
    State,
)

User = get_user_model()


class RegionScopedPermissionTests(TestCase):
    """
    This class is responsible for testing the region-scoped permission system.
    """

    def setUp(self):
        self.factory = RequestFactory()
        
        # Create regions
        self.region_ne = Region.objects.create(code="NE", name="Nordeste")
        self.region_s = Region.objects.create(code="S", name="Sul")

        # Create states
        self.state_ne = State.objects.create(code="N1", name="State NE", region=self.region_ne)
        self.state_s = State.objects.create(code="S1", name="State S", region=self.region_s)

        # Create intermediate regions
        self.intermediate_ne = IntermediateRegion.objects.create(
            code="1001", name="Intermediate NE", state=self.state_ne
        )
        self.intermediate_s = IntermediateRegion.objects.create(
            code="2001", name="Intermediate S", state=self.state_s
        )

        # Create immediate regions
        self.immediate_ne = ImmediateRegion.objects.create(
            code="100101", name="Immediate NE", intermediate_region=self.intermediate_ne
        )
        self.immediate_s = ImmediateRegion.objects.create(
            code="200101", name="Immediate S", intermediate_region=self.intermediate_s
        )

        # Create municipalities
        self.municipality_ne = Municipality.objects.create(
            code="1000001", name="City NE", immediate_region=self.immediate_ne
        )
        self.municipality_s = Municipality.objects.create(
            code="2000001", name="City S", immediate_region=self.immediate_s
        )

        # Create resource permissions
        self.view_perm = ResourcePermission.objects.create(
            name="View Municipality",
            codename="view_cities_municipality",
            permission_type="view",
            resource_name="cities.municipality",
        )
        self.change_perm = ResourcePermission.objects.create(
            name="Change Municipality",
            codename="change_cities_municipality",
            permission_type="change",
            resource_name="cities.municipality",
        )

        # Create groups
        self.group_ne = Group.objects.create(name="Region - Nordeste")
        self.group_global = Group.objects.create(name="Cities - Global")

        # Create user
        self.user = User.objects.create_user(
            email="user@example.com",
            username="testuser",
            password="password",
            is_staff=True,
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_state"),
            Permission.objects.get(codename="change_state"),
            Permission.objects.get(codename="view_municipality"),
            Permission.objects.get(codename="change_municipality"),
        )

    def _make_request(self, user=None):
        request = self.factory.get("/")
        request.user = user or self.user
        return request


class CheckResourcePermissionTests(RegionScopedPermissionTests):
    """
    This class is responsible for testing the check_resource_permission function.
    """

    def test_user_with_region_scoped_permission_can_access_region(self):
        # Setup: Give user region-scoped view permission for Nordeste
        self.user.groups.add(self.group_ne)
        GroupResourcePermission.objects.create(
            group=self.group_ne,
            resource_permission=self.view_perm,
            region=self.region_ne,
        )

        result = check_resource_permission(
            self.user, "cities.municipality", "view", region=self.region_ne
        )
        self.assertTrue(result)

    def test_user_with_region_scoped_permission_cannot_access_other_region(self):
        # Setup: Give user region-scoped view permission for Nordeste only
        self.user.groups.add(self.group_ne)
        GroupResourcePermission.objects.create(
            group=self.group_ne,
            resource_permission=self.view_perm,
            region=self.region_ne,
        )

        result = check_resource_permission(
            self.user, "cities.municipality", "view", region=self.region_s
        )
        self.assertFalse(result)

    def test_user_with_global_permission_can_access_any_region(self):
        # Setup: Give user global view permission (region=None)
        self.user.groups.add(self.group_global)
        GroupResourcePermission.objects.create(
            group=self.group_global,
            resource_permission=self.view_perm,
            region=None,
        )

        # Can access Nordeste
        self.assertTrue(
            check_resource_permission(
                self.user, "cities.municipality", "view", region=self.region_ne
            )
        )
        # Can access Sul
        self.assertTrue(
            check_resource_permission(
                self.user, "cities.municipality", "view", region=self.region_s
            )
        )

    def test_user_without_permission_cannot_access(self):
        result = check_resource_permission(
            self.user, "cities.municipality", "view", region=self.region_ne
        )
        self.assertFalse(result)


class GetUserPermittedRegionsTests(RegionScopedPermissionTests):
    """
    This class is responsible for testing the get_user_permitted_regions function.
    """

    def test_returns_none_for_global_access(self):
        self.user.groups.add(self.group_global)
        GroupResourcePermission.objects.create(
            group=self.group_global,
            resource_permission=self.view_perm,
            region=None,
        )

        result = get_user_permitted_regions(self.user, "cities.municipality", "view")
        self.assertIsNone(result)

    def test_returns_region_ids_for_scoped_access(self):
        self.user.groups.add(self.group_ne)
        GroupResourcePermission.objects.create(
            group=self.group_ne,
            resource_permission=self.view_perm,
            region=self.region_ne,
        )

        result = get_user_permitted_regions(self.user, "cities.municipality", "view")
        self.assertEqual(result, [self.region_ne.id])

    def test_returns_empty_list_for_no_access(self):
        result = get_user_permitted_regions(self.user, "cities.municipality", "view")
        self.assertEqual(result, [])


class RegionScopedAdminMixinTests(RegionScopedPermissionTests):
    """
    This class is responsible for testing the RegionScopedAdminMixin behavior.
    """

    def setUp(self):
        super().setUp()
        self.admin_state = StateAdmin(State, admin.site)
        self.admin_municipality = MunicipalityAdmin(Municipality, admin.site)

    def test_superuser_can_access_all(self):
        superuser = User.objects.create_superuser(
            email="super@example.com", username="super", password="password"
        )
        request = self._make_request(user=superuser)

        self.assertTrue(self.admin_state.has_change_permission(request, obj=self.state_ne))
        self.assertTrue(self.admin_state.has_change_permission(request, obj=self.state_s))

    def test_user_can_change_objects_in_permitted_region(self):
        self.user.groups.add(self.group_ne)
        GroupResourcePermission.objects.create(
            group=self.group_ne,
            resource_permission=self.change_perm,
            region=self.region_ne,
        )
        # Also need view for the admin
        GroupResourcePermission.objects.create(
            group=self.group_ne,
            resource_permission=self.view_perm,
            region=self.region_ne,
        )

        request = self._make_request()
        self.assertTrue(self.admin_municipality.has_change_permission(request, obj=self.municipality_ne))

    def test_user_cannot_change_objects_outside_permitted_region(self):
        self.user.groups.add(self.group_ne)
        GroupResourcePermission.objects.create(
            group=self.group_ne,
            resource_permission=self.change_perm,
            region=self.region_ne,
        )

        request = self._make_request()
        self.assertFalse(self.admin_municipality.has_change_permission(request, obj=self.municipality_s))

    def test_queryset_filtered_by_region(self):
        self.user.groups.add(self.group_ne)
        GroupResourcePermission.objects.create(
            group=self.group_ne,
            resource_permission=self.view_perm,
            region=self.region_ne,
        )

        request = self._make_request()
        qs = self.admin_municipality.get_queryset(request)

        self.assertIn(self.municipality_ne, qs)
        self.assertNotIn(self.municipality_s, qs)

    def test_global_user_sees_all_in_queryset(self):
        self.user.groups.add(self.group_global)
        GroupResourcePermission.objects.create(
            group=self.group_global,
            resource_permission=self.view_perm,
            region=None,
        )

        request = self._make_request()
        qs = self.admin_municipality.get_queryset(request)

        self.assertIn(self.municipality_ne, qs)
        self.assertIn(self.municipality_s, qs)
