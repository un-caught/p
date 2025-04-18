from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import PTWForm, SafetyPrecaution, WorkLocationIsolation, PersonalSafety, NHISForm, Hazards, Member, NHISComment, PTWComment, LOCATION_CHOICES

from django.forms.widgets import ClearableFileInput



class CreateUserForm(UserCreationForm):
    group_choices = forms.ChoiceField(
        choices=[('staff', 'Staff'), ('vendor', 'Vendor Supervisor')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    location_choices = forms.ChoiceField(
        choices=LOCATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Location'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'first_name','last_name']

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user



class PTWSubmissionForm(forms.ModelForm):
    class Meta:
        model = PTWForm
        fields = ['location', 'work_description', 'equipment_tools_materials', 'risk_assessment_done','attachment','project_attachment',
                  'start_datetime', 'duration', 'days', 'workers_count', 'department','contractor','contractor_supervisor',
                  'work_place', 'work_location_isolation', 'personal_safety', 'additional_precautions', 'supervisor_name',
                  'applicant_name', 'applicant_date', 'applicant_sign', 'facility_manager_name', 'facility_manager_date', 'facility_manager_sign', 'certificates_required',
                  'valid_from', 'valid_to', 'initials', 'contractor_name', 'contractor_date', 'contractor_sign', 'hseq_name', 'hseq_date', 'hseq_sign', 'manager_name', 'manager_date', 'manager_sign']


    #Work Details
    location = forms.ChoiceField(choices=LOCATION_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    work_description = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    equipment_tools_materials = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    risk_assessment_done = forms.ChoiceField(choices=[('yes', 'Yes'), ('no', 'No')], widget=forms.Select(attrs={'class': 'form-select'}))
    attachment = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}), required=False)

    #Work Duration and Personnel
    start_datetime = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    duration = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    days = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}))
    workers_count = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}))
    department = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    contractor = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    contractor_supervisor = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))

    # Safety Precautions
    work_place = forms.ModelMultipleChoiceField(
        queryset=SafetyPrecaution.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False  # Make it optional to select any option
    )

    work_location_isolation = forms.ModelMultipleChoiceField(
        queryset=WorkLocationIsolation.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False  # Make it optional to select any option
    )

    personal_safety = forms.ModelMultipleChoiceField(
        queryset=PersonalSafety.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False  # Make it optional to select any option
    )

    additional_precautions = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=False)

    #Permit Applicant
    supervisor_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    applicant_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    applicant_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    applicant_sign = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))

    #Facility Manager
    facility_manager_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    facility_manager_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    facility_manager_sign = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    certificates_required = forms.ChoiceField(choices=[
        ('CERTIFICATE_FOR_EXCAVATION_WORK', 'CERTIFICATE FOR EXCAVATION WORK'),
        ('CERTIFICATE_FOR_HOT_WORK', 'CERTIFICATE FOR HOT WORK'),
        ('CERTIFICATE_FOR_ELECTRICAL_WORK', 'CERTIFICATE FOR ELECTRICAL WORK'),
        ('GAS_TEST_FORM', 'GAS TEST FORM'),
        ('CERTIFICATE_FOR_CONFINED_SPACES', 'CERTIFICATE FOR CONFINED SPACES'),
        ('NOT_APPLICABLE', 'NOT APPLICABLE'),
        ], widget=forms.Select(attrs={'class': 'form-select'}))

    #Validity And Renewal Of Permit
    valid_from = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}), required=False)
    valid_to = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}), required=False)
    initials = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)

    #Contractor
    contractor_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    contractor_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    contractor_sign = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    project_attachment = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}), required=False)

    #HSEQ
    hseq_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    hseq_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}), required=False)
    hseq_sign = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)

    #Manager
    manager_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    manager_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}), required=False)
    manager_sign = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)


class NHISSubmissionForm(forms.ModelForm):
    class Meta:
        model = NHISForm
        fields = ['location', 'date', 'hazard', 'risk_type', 'ram_rating', 'observation',
        'action_taken', 'preventive_action', 'responsible_party', 'target_date', 'observed_by', 'dept', 'observed_date']



    #General Information
    location = forms.ChoiceField(choices=LOCATION_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))

    #Hazard Identification
    hazard = forms.ModelMultipleChoiceField(
        queryset=Hazards.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False  # Make it optional to select any option
    )

    risk_type = forms.ChoiceField(choices=[('UA', 'UA (Unsafe Act)'),
        ('UC', 'UC (Unsafe Condition)'),
        ('NM', 'NM (Near Miss)'),
        ('ACD', 'ACD (Accident)'),
        ('NC', 'NC (Non Conformity)'),
        ], widget=forms.Select(attrs={'class': 'form-select'}))

    ram_rating = forms.ChoiceField(choices=[('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
        ], widget=forms.Select(attrs={'class': 'form-select'}))

    #Observations
    observation = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=False)

    #Immediate Action Taken
    action_taken = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=False)

    #Preventive Actions
    preventive_action = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=False)

    #Responsible Party And Target
    responsible_party = forms.ChoiceField(choices=[('HSEQ', 'HSEQ'),], widget=forms.RadioSelect(attrs={'class': 'form-check-input'}), required=True,)
    target_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))

    #Observed By
    observed_by = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'}))
    dept = forms.ChoiceField(choices=[
        ('Admin', 'Admin'),
        ('BDS', 'BDS'),
        ('DC', 'DC'),
        ('ER', 'ER'),
        ('FVC', 'FVC'),
        ('HR', 'HR'),
        ('HSE', 'HSE'),
        ('IAC', 'IAC'),
        ('IT', 'IT'),
        ('LRC', 'LRC'),
        ('TS', 'TS'),
    ], widget=forms.Select(attrs={'class': 'form-select'}))
    observed_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))


class CommentForm(forms.ModelForm):
    class Meta:
        model = NHISComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Add your comment here...'}),
        }


class RejectForm(forms.Form):
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Please provide a reason for rejection'}),
        required=True
    )


class PTWCommentForm(forms.ModelForm):
    class Meta:
        model = PTWComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Add your comment here...'}),
        }


class PTWRejectForm(forms.Form):
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Please provide a reason for rejection'}),
        required=True
    )