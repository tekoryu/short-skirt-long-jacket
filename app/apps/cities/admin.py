from django.contrib import admin
from .models import Region, State, IntermediateRegion, ImmediateRegion, Municipality


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'state_count']
    search_fields = ['code', 'name']
    ordering = ['name']
    
    def state_count(self, obj):
        return obj.states.count()
    state_count.short_description = 'Number of States'


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ['code', 'abbreviation', 'name', 'region', 'latitude', 'longitude']
    search_fields = ['code', 'abbreviation', 'name', 'region__name']
    list_filter = ['region']
    ordering = ['name']


@admin.register(IntermediateRegion)
class IntermediateRegionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'state']
    list_filter = ['state']
    search_fields = ['code', 'name', 'state__name']
    ordering = ['name']


@admin.register(ImmediateRegion)
class ImmediateRegionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'intermediate_region', 'state_name']
    list_filter = ['intermediate_region__state']
    search_fields = ['code', 'name', 'intermediate_region__name']
    ordering = ['name']
    
    def state_name(self, obj):
        return obj.intermediate_region.state.name
    state_name.short_description = 'State'


@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_capital', 'latitude', 'longitude', 'area_code', 'timezone', 'immediate_region', 'state_name']
    list_filter = ['is_capital', 'immediate_region__intermediate_region__state', 'timezone']
    search_fields = ['code', 'name', 'siafi_id', 'area_code', 'immediate_region__name']
    ordering = ['name']
    list_editable = ['is_capital']
    
    def state_name(self, obj):
        return obj.immediate_region.intermediate_region.state.name
    state_name.short_description = 'State'
