from django.db import models


class State(models.Model):
    """Brazilian state model"""
    code = models.CharField(max_length=2, unique=True, verbose_name="State Code")
    name = models.CharField(max_length=100, verbose_name="State Name")
    
    class Meta:
        verbose_name = "State"
        verbose_name_plural = "States"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class IntermediateRegion(models.Model):
    """Intermediate geographic region model"""
    code = models.CharField(max_length=4, unique=True, verbose_name="Region Code")
    name = models.CharField(max_length=200, verbose_name="Region Name")
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='intermediate_regions')
    
    class Meta:
        verbose_name = "Intermediate Region"
        verbose_name_plural = "Intermediate Regions"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.state.name}"


class ImmediateRegion(models.Model):
    """Immediate geographic region model"""
    code = models.CharField(max_length=6, unique=True, verbose_name="Region Code")
    name = models.CharField(max_length=200, verbose_name="Region Name")
    intermediate_region = models.ForeignKey(IntermediateRegion, on_delete=models.CASCADE, related_name='immediate_regions')
    
    class Meta:
        verbose_name = "Immediate Region"
        verbose_name_plural = "Immediate Regions"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.intermediate_region.name}"


class Municipality(models.Model):
    """Brazilian municipality model"""
    code = models.CharField(max_length=7, unique=True, verbose_name="Municipality Code")
    name = models.CharField(max_length=200, verbose_name="Municipality Name")
    immediate_region = models.ForeignKey(ImmediateRegion, on_delete=models.CASCADE, related_name='municipalities')
    
    class Meta:
        verbose_name = "Municipality"
        verbose_name_plural = "Municipalities"
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.immediate_region.intermediate_region.state.name}"
