from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .models import ResourcePermission, UserPermission, GroupResourcePermission

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    """
    Custom user registration form with additional fields.
    """
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone = forms.CharField(max_length=20, required=False)
    department = forms.CharField(max_length=100, required=False)
    position = forms.CharField(max_length=100, required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'department', 'position')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['first_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['phone'].widget.attrs.update({'class': 'form-control'})
        self.fields['department'].widget.attrs.update({'class': 'form-control'})
        self.fields['position'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone = self.cleaned_data['phone']
        user.department = self.cleaned_data['department']
        user.position = self.cleaned_data['position']
        if commit:
            user.save()
        return user


class PermissionAssignmentForm(forms.ModelForm):
    """
    Form for assigning permissions to users.
    """
    class Meta:
        model = UserPermission
        fields = ['user', 'resource_permission', 'expires_at']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'resource_permission': forms.Select(attrs={'class': 'form-control'}),
            'expires_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active users and permissions
        self.fields['user'].queryset = User.objects.filter(is_active=True).order_by('email')
        self.fields['resource_permission'].queryset = ResourcePermission.objects.filter(is_active=True).order_by('resource_name', 'permission_type')


class GroupResourcePermissionForm(forms.ModelForm):
    """
    This class is responsible for creating forms to assign resource permissions to groups.
    """
    class Meta:
        model = GroupResourcePermission
        fields = ['group', 'resource_permission']
        widgets = {
            'group': forms.Select(attrs={'class': 'form-control'}),
            'resource_permission': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active groups and permissions
        self.fields['group'].queryset = Group.objects.all().order_by('name')
        self.fields['resource_permission'].queryset = ResourcePermission.objects.filter(is_active=True).order_by('resource_name', 'permission_type')


class ResourcePermissionForm(forms.ModelForm):
    """
    Form for creating/editing resource permissions.
    """
    class Meta:
        model = ResourcePermission
        fields = ['name', 'codename', 'permission_type', 'resource_name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'codename': forms.TextInput(attrs={'class': 'form-control'}),
            'permission_type': forms.Select(attrs={'class': 'form-control'}),
            'resource_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UserSearchForm(forms.Form):
    """
    Form for searching users in permission management.
    """
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by email, username, or name...'
        })
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by department...'
        })
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class PermissionSearchForm(forms.Form):
    """
    Form for searching permissions.
    """
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, resource, or description...'
        })
    )
    permission_type = forms.ChoiceField(
        choices=[('', 'All Types')] + ResourcePermission.PERMISSION_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    resource_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by resource name...'
        })
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

