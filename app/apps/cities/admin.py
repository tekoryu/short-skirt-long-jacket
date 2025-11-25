from django.contrib import admin

from .mixins import RegionScopedAdminMixin
from .models import Region, State, IntermediateRegion, ImmediateRegion, Municipality


@admin.register(Region)
class RegionAdmin(RegionScopedAdminMixin, admin.ModelAdmin):
    list_display = ['code', 'name', 'state_count']
    search_fields = ['code', 'name']
    ordering = ['name']
    
    def state_count(self, obj):
        return obj.states.count()
    state_count.short_description = 'Number of States'


@admin.register(State)
class StateAdmin(RegionScopedAdminMixin, admin.ModelAdmin):
    list_display = ['code', 'abbreviation', 'name', 'region', 'latitude', 'longitude']
    search_fields = ['code', 'abbreviation', 'name', 'region__name']
    list_filter = ['region']
    ordering = ['name']


@admin.register(IntermediateRegion)
class IntermediateRegionAdmin(RegionScopedAdminMixin, admin.ModelAdmin):
    list_display = ['code', 'name', 'state']
    list_filter = ['state']
    search_fields = ['code', 'name', 'state__name']
    ordering = ['name']


@admin.register(ImmediateRegion)
class ImmediateRegionAdmin(RegionScopedAdminMixin, admin.ModelAdmin):
    list_display = ['code', 'name', 'intermediate_region', 'state_name']
    list_filter = ['intermediate_region__state']
    search_fields = ['code', 'name', 'intermediate_region__name']
    ordering = ['name']
    
    def state_name(self, obj):
        return obj.intermediate_region.state.name
    state_name.short_description = 'State'


@admin.register(Municipality)
class MunicipalityAdmin(RegionScopedAdminMixin, admin.ModelAdmin):
    list_display = ['code', 'name', 'is_capital', 'seaf_category', 'mayor_name', 'mayor_party', 'mayor_mandate_period', 'state_name']
    list_filter = ['is_capital', 'seaf_category', 'immediate_region__intermediate_region__state', 'timezone', 'mayor_party']
    search_fields = ['code', 'name', 'siafi_id', 'area_code', 'immediate_region__name', 'mayor_name', 'mayor_party']
    ordering = ['name']
    list_editable = ['is_capital']
    readonly_fields = ['mayor_data_updated_at', 'wiki_data_updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'is_capital', 'siafi_id', 'immediate_region', 'seaf_category')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'area_code', 'timezone')
        }),
        ('Mayor Information', {
            'fields': ('mayor_name', 'mayor_party', 'mayor_mandate_start', 'mayor_mandate_end', 'wikipedia_url', 'mayor_data_updated_at')
        }),
        ('Wikipedia - Basic Data', {
            'fields': ('wiki_demonym', 'wiki_climate', 'wiki_altitude', 'wiki_total_area', 'wiki_population', 'wiki_density'),
            'classes': ('collapse',)
        }),
        ('Wikipedia - Geographic Data', {
            'fields': ('wiki_metropolitan_region', 'wiki_bordering_municipalities', 'wiki_distance_to_capital', 'wiki_foundation_date'),
            'classes': ('collapse',)
        }),
        ('Wikipedia - Economic & Social Data', {
            'fields': ('wiki_idh', 'wiki_gini', 'wiki_gdp', 'wiki_gdp_per_capita'),
            'classes': ('collapse',)
        }),
        ('Wikipedia - Mayor Information', {
            'fields': ('wiki_mayor_name', 'wiki_mayor_party', 'wiki_mayor_mandate_start', 'wiki_mayor_mandate_end'),
            'classes': ('collapse',)
        }),
        ('Wikipedia - Other', {
            'fields': ('wiki_council_members', 'wiki_postal_code', 'wiki_website', 'wiki_data_updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def state_name(self, obj):
        return obj.immediate_region.intermediate_region.state.name
    state_name.short_description = 'State'
    
    def mayor_mandate_period(self, obj):
        if obj.mayor_mandate_start and obj.mayor_mandate_end:
            return f"{obj.mayor_mandate_start}-{obj.mayor_mandate_end}"
        return "-"
    mayor_mandate_period.short_description = 'Mandate Period'
