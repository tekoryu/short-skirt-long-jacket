from django.contrib import admin
from .models import State, IntermediateRegion, ImmediateRegion, Municipality


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['code', 'name']
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
    list_display = ['code', 'name', 'immediate_region', 'state_name']
    list_filter = ['immediate_region__intermediate_region__state']
    search_fields = ['code', 'name', 'immediate_region__name']
    ordering = ['name']
    
    def state_name(self, obj):
        return obj.immediate_region.intermediate_region.state.name
    state_name.short_description = 'State'
