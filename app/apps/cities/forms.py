from django import forms
from .models import Municipality


class MunicipalityEditForm(forms.ModelForm):
    """
    This class is responsible for creating a form to edit municipality data with proper pt_BR labels.
    """
    
    seaf_category = forms.TypedChoiceField(
        label='Categoria SEAF',
        choices=[
            ('', '---------'),
            (1, 'Categoria 1'),
            (2, 'Categoria 2'),
            (3, 'Categoria 3'),
            (4, 'Categoria 4'),
        ],
        coerce=lambda x: int(x) if x else None,
        required=False,
        empty_value=None,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Municipality
        fields = [
            'seaf_category',
            'mayor_name',
            'mayor_party',
            'mayor_mandate_start',
            'mayor_mandate_end',
            'wiki_demonym',
            'wiki_altitude',
            'wiki_total_area',
            'wiki_population',
            'wiki_density',
            'wiki_climate',
            'wiki_idh',
            'wiki_gdp',
            'wiki_gdp_per_capita',
            'wiki_website',
            'wiki_metropolitan_region',
            'wiki_bordering_municipalities',
            'wiki_distance_to_capital',
            'wiki_foundation_date',
            'wiki_council_members',
            'wiki_postal_code',
            'wiki_gini',
        ]
        
        labels = {
            'mayor_name': 'Nome do Prefeito',
            'mayor_party': 'Partido do Prefeito',
            'mayor_mandate_start': 'Início do Mandato',
            'mayor_mandate_end': 'Fim do Mandato',
            'wiki_demonym': 'Gentílico',
            'wiki_altitude': 'Altitude',
            'wiki_total_area': 'Área Total',
            'wiki_population': 'População',
            'wiki_density': 'Densidade Demográfica',
            'wiki_climate': 'Clima',
            'wiki_idh': 'IDH',
            'wiki_gdp': 'PIB',
            'wiki_gdp_per_capita': 'PIB per Capita',
            'wiki_website': 'Site Oficial',
            'wiki_metropolitan_region': 'Região Metropolitana',
            'wiki_bordering_municipalities': 'Municípios Limítrofes',
            'wiki_distance_to_capital': 'Distância até a Capital',
            'wiki_foundation_date': 'Data de Fundação',
            'wiki_council_members': 'Número de Vereadores',
            'wiki_postal_code': 'CEP',
            'wiki_gini': 'Coeficiente de Gini',
        }
        
        widgets = {
            'mayor_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nome completo do prefeito'}),
            'mayor_party': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Sigla do partido'}),
            'mayor_mandate_start': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Ano'}),
            'mayor_mandate_end': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Ano'}),
            'wiki_demonym': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: paulistano, carioca'}),
            'wiki_altitude': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: 760 m'}),
            'wiki_total_area': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: 1521.11 km²'}),
            'wiki_population': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: 12.325.232'}),
            'wiki_density': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: 7.398,26 hab./km²'}),
            'wiki_climate': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Subtropical'}),
            'wiki_idh': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: 0.805'}),
            'wiki_gdp': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: R$ 699.28 bilhões'}),
            'wiki_gdp_per_capita': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: R$ 56.584,26'}),
            'wiki_website': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'https://'}),
            'wiki_metropolitan_region': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nome da região metropolitana'}),
            'wiki_bordering_municipalities': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Liste os municípios limítrofes'}),
            'wiki_distance_to_capital': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: 358 km'}),
            'wiki_foundation_date': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: 25 de janeiro de 1554'}),
            'wiki_council_members': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Número'}),
            'wiki_postal_code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: 01000-000'}),
            'wiki_gini': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: 0.62'}),
        }
        
        help_texts = {
            'mayor_mandate_start': 'Ano de início do mandato (ex: 2021)',
            'mayor_mandate_end': 'Ano de término do mandato (ex: 2024)',
            'wiki_idh': 'Índice de Desenvolvimento Humano',
            'wiki_gini': 'Coeficiente de desigualdade social (0 a 1)',
        }
    
    def clean_wiki_website(self):
        """
        This method is responsible for skipping URL validation for wiki_website field.
        """
        return self.cleaned_data.get('wiki_website', '')
    
    def clean(self):
        """
        This method is responsible for validating only changed fields.
        """
        cleaned_data = super().clean()
        
        # If this is an update (instance exists), only validate changed fields
        if self.instance and self.instance.pk:
            for field_name in list(self.errors.keys()):
                # Skip validation errors for fields that weren't changed
                if field_name not in self.changed_data:
                    del self.errors[field_name]
                    # Restore original value for unchanged fields with errors
                    if field_name in cleaned_data:
                        cleaned_data[field_name] = getattr(self.instance, field_name)
        
        return cleaned_data

