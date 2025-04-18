import datetime
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from .models import LeaveRequest, LeaveType, LeavePeriod, LeaveBalance # Import new models

# Define year choices dynamically
current_year = datetime.datetime.now().year
YEAR_CHOICES = [(year, year) for year in range(current_year - 2, current_year + 3)]

class LeaveRequestForm(forms.ModelForm):
    active_year = forms.ChoiceField(
        choices=YEAR_CHOICES,
        initial=current_year,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    relief_officer = forms.ModelChoiceField(
        queryset=User.objects.none(), # Queryset set in __init__
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        label="Select Relief Officer"
    )
    hod_line_manager = forms.ModelChoiceField(
        queryset=User.objects.none(), # Queryset set in __init__
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        label="Select HOD / Line Manager"
    )

    class Meta:
        model = LeaveRequest
        fields = [
            'active_year', 'leave_type', 'reason', 'address', 
            'phone_number', 'attachment', 'relief_officer', 'hod_line_manager'
        ]
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter Purpose...'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter Address...'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'reason': 'Purpose', # Relabel
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None) # Get user passed from view
        super().__init__(*args, **kwargs)
        
        if user:
            # Filter relief officers: Eligible, not HOD, not self
            self.fields['relief_officer'].queryset = User.objects.filter(
                member__is_relief_eligible=True, 
                member__is_hod_manager=False
            ).exclude(pk=user.pk).select_related('member')
            
            # Filter HODs/Managers
            self.fields['hod_line_manager'].queryset = User.objects.filter(
                member__is_hod_manager=True
            ).select_related('member')

        # Make fields optional if needed based on model definition (blank=True)
        self.fields['address'].required = False
        self.fields['phone_number'].required = False
        self.fields['attachment'].required = False # Base requirement is False, checked in clean()

    def clean(self):
        cleaned_data = super().clean()
        leave_type = cleaned_data.get('leave_type')
        attachment = cleaned_data.get('attachment')
        
        # Conditional attachment requirement
        if leave_type and leave_type.name == 'Exam/Study Leave' and not attachment:
            self.add_error('attachment', 'Attachment is required for Exam/Study Leave.')

        # Note: Validation for outstanding days vs requested duration will be done 
        # in the view after the formset is processed, as we need the total duration from the formset.
            
        return cleaned_data


class LeavePeriodForm(forms.ModelForm):
    class Meta:
        model = LeavePeriod
        fields = ['start_date', 'duration']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm leave-period-start'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control form-control-sm leave-period-duration', 'min': '1'}),
        }

    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if start_date and start_date < datetime.date.today():
            raise ValidationError("Start date cannot be in the past.")
        # Add weekend check if needed, although calculation handles it
        # if start_date and start_date.weekday() >= 5: # 5 = Saturday, 6 = Sunday
        #     raise ValidationError("Start date cannot be on a weekend.")
        return start_date

    def clean_duration(self):
        duration = self.cleaned_data.get('duration')
        if duration is not None and duration <= 0:
            raise ValidationError("Duration must be a positive number of days.")
        return duration

# Create the inline formset
BaseLeavePeriodFormSet = inlineformset_factory(
    LeaveRequest, 
    LeavePeriod, 
    form=LeavePeriodForm, 
    extra=0, # Start with zero extra forms
    can_delete=True, 
    min_num=1, # Require at least one period
    validate_min=True,
)

class LeaveApprovalForm(forms.ModelForm): # Keep this form as is for now
    class Meta:
        model = LeaveRequest
        fields = ['status', 'rejection_reason']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'rejection_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        if status == 'rejected' and not rejection_reason:
            raise forms.ValidationError("Please provide a reason for rejection.")
        
        return cleaned_data

class LeaveTypeForm(forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = ['name', 'description', 'max_days']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'max_days': forms.NumberInput(attrs={'class': 'form-control'}),
        }
