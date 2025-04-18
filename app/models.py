from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Centralized location choices for the entire application
LOCATION_CHOICES = [
    ('Lekki', 'HQ - Lekki'),
    ('Ikorodu', 'CGS - Ikorodu'),
    ('Ibeju_Lekki', 'Optimera - Ibeju Lekki'),
    ('Portharcourt', 'LPG - Port Harcourt'),
]

# Create your models here.
class Member(models.Model):

    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, null=True)
    email = models.CharField(max_length=200, null=True)
    phone = models.CharField(max_length=20, null=True, blank=True) # Max length adjusted based on user feedback, but keeping 20 for now as 16 seemed too specific without country code considerations.
    address = models.CharField(max_length=255, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, null=True)
    # Fields to identify roles for leave management
    is_hod_manager = models.BooleanField(default=False)
    is_relief_eligible = models.BooleanField(default=True) # Default to True, admin can disable

    def customer(self):
        return self.name


class SafetyPrecaution(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name}"

class WorkLocationIsolation(models.Model):
    name = models.CharField(max_length=255)
    def __str__(self):
        return self.name

class PersonalSafety(models.Model):
    name = models.CharField(max_length=255)
    def __str__(self):
        return self.name

class Hazards(models.Model):
    name = models.CharField(max_length=255)
    def __str__(self):
        return self.name


class PTWForm(models.Model):
    # Section 1: Work Details
    form_number = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    date_submitted = models.DateTimeField(auto_now_add=True, null=True)
    location = models.CharField(max_length=255, choices=LOCATION_CHOICES, blank=True, null=True)
    work_description = models.TextField(null=True)
    equipment_tools_materials = models.TextField(null=True)
    risk_assessment_done = models.CharField(max_length=3, choices=[('yes', 'Yes'), ('no', 'No')], null=True)
    attachment = models.FileField(upload_to='attachments/', null=True, blank=True)
    project_attachment = models.FileField(upload_to='attachments/', null=True, blank=True)


    # Section 2: Work Duration and Personnel
    start_datetime = models.DateTimeField(null=True)
    duration = models.CharField(max_length=255, null=True)
    days = models.IntegerField(null=True)
    workers_count = models.IntegerField(null=True)
    department = models.CharField(max_length=255, null=True)
    contractor = models.CharField(max_length=255, null=True)
    contractor_supervisor = models.CharField(max_length=255, null=True)

    # Section 3: Safety Precautions
    work_place = models.ManyToManyField(SafetyPrecaution, blank=True)
    work_location_isolation = models.ManyToManyField(WorkLocationIsolation, blank=True)
    personal_safety = models.ManyToManyField(PersonalSafety, blank=True)
    additional_precautions = models.TextField(blank=True)

     # Section 4: Permit Applicant
    supervisor_name = models.CharField(max_length=255, null=True)
    applicant_name = models.CharField(max_length=255, null=True)
    applicant_date = models.DateField(null=True)
    applicant_sign = models.CharField(max_length=255, null=True)

     # Section 5: Facility Manager
    facility_manager_name = models.CharField(max_length=255, null=True)
    facility_manager_date = models.DateField(null=True)
    facility_manager_sign = models.CharField(max_length=255, null=True)
    certificates_required = models.CharField(max_length=255, choices=[
        ('CERTIFICATE_FOR_EXCAVATION_WORK', 'CERTIFICATE_FOR_EXCAVATION_WORK'),
        ('CERTIFICATE_FOR_HOT_WORK', 'CERTIFICATE_FOR_HOT_WORK'),
        ('CERTIFICATE_FOR_ELECTRICAL_WORK', 'CERTIFICATE_FOR_ELECTRICAL_WORK'),
        ('GAS_TEST_FORM', 'GAS_TEST_FORM'),
        ('CERTIFICATE_FOR_CONFINED_SPACES', 'CERTIFICATE_FOR_CONFINED_SPACES'),
        ('NOT_APPLICABLE', 'NOT_APPLICABLE'),
    ], blank=True, null=True)

    # Section 6: Validity and Renewal
    valid_from = models.DateField(null=True)
    valid_to = models.DateField(null=True)
    initials = models.CharField(max_length=100, null=True)

    # Section 7: Contractor
    contractor_name = models.CharField(max_length=255, null=True)
    contractor_date = models.DateField(null=True)
    contractor_sign = models.CharField(max_length=255, null=True)

    # Section 8: HSEQ
    hseq_name = models.CharField(max_length=255, null=True)
    hseq_date = models.DateField(null=True)
    hseq_sign = models.CharField(max_length=255, null=True)

    # Section 9: Manager
    manager_name = models.CharField(max_length=255, null=True)
    manager_date = models.DateField(null=True)
    manager_sign = models.CharField(max_length=255, null=True)


    # Approval and rejection tracking
    supervisor_approved_at = models.DateTimeField(null=True, blank=True)
    supervisor_approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='ptw_supervisor_approvals')
    manager_approved_at = models.DateTimeField(null=True, blank=True)
    manager_approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='ptw_manager_approvals')
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='ptw_rejections')
    rejection_reason = models.TextField(null=True, blank=True)

    status = models.CharField(
        max_length=30,
        choices=[
            ('awaiting_supervisor', 'Awaiting Supervisor Approval'),
            ('supervisor_signed', 'Supervisor Signed'),
            ('awaiting_manager', 'Awaiting Manager Approval'),
            ('manager_signed', 'Manager Signed'),
            ('approved', 'Approved'),
            ('rejected_by_supervisor', 'Rejected by Supervisor'),
            ('rejected_by_manager', 'Rejected by Manager'),
            ('disapproved', 'Disapproved'),
        ],
        default='awaiting_supervisor',
    )

    def save(self, *args, **kwargs):
        # Generate form number if it doesn't exist
        if not self.form_number:
            from datetime import datetime
            year = datetime.now().year
            last_form = PTWForm.objects.filter(form_number__startswith=f'PTW-{year}').order_by('-form_number').first()
            if last_form:
                try:
                    last_number = int(last_form.form_number.split('-')[-1])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            self.form_number = f'PTW-{year}-{new_number:03d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"PTW Form {self.form_number or self.id}"


class NHISForm(models.Model):
    # Section 1: General Information
    form_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    date_submitted = models.DateTimeField(auto_now_add=True, null=True)
    location = models.CharField(max_length=50, choices=LOCATION_CHOICES, blank=True, null=True)
    date = models.DateField(null=True)
    question = models.CharField(max_length=7, choices=[('option1', 'Option 1'), ('option2', 'Option 2')], null=True)

    # Section 2: Hazard Identification
    hazard = models.ManyToManyField(Hazards, blank=True)
    risk_type = models.CharField(max_length=255, choices=[
        ('UA', 'UA (Unsafe Act)'),
        ('UC', 'UC (Unsafe Condition)'),
        ('NM', 'NM (Near Miss)'),
        ('ACD', 'ACD (Accident)'),
        ('NC', 'NC (Non-Conformity)'),
    ], blank=True, null=True)
    ram_rating = models.CharField(max_length=255, choices=[
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ], blank=True, null=True)

    # Section 3: Obeservation
    observation = models.TextField(blank=True)

     # Section 4: Immediate Action Taken
    action_taken = models.TextField(blank=True)

     # Section 5: Preventive Action
    preventive_action = models.TextField(blank=True)

    # Section 6: Responsible Party And Target
    responsible_party = models.CharField(max_length=7, choices=[('HSEQ', 'HSEQ')], default='HSEQ', null=True)
    target_date = models.DateField(null=True)

    # Section 7: Observed By
    observed_by = models.CharField(max_length=255, null=True)
    dept = models.CharField(max_length=255, choices=[
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
    ], blank=True, null=True)
    observed_date = models.DateField(null=True)

    status = models.CharField(
        max_length=25,
        choices=[
            ('awaiting_supervisor', 'Awaiting Supervisor Approval'),
            ('approved', 'Approved'),
            ('rejected_by_supervisor', 'Rejected by Supervisor'),
            # Keeping these for backward compatibility with existing data
            ('awaiting_manager', 'Awaiting Manager Approval'),
            ('rejected_by_manager', 'Rejected by Manager'),
        ],
        default='awaiting_supervisor',
    )

    # Approval tracking
    supervisor_approved_at = models.DateTimeField(null=True, blank=True)
    supervisor_approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='nhis_supervisor_approvals')
    manager_approved_at = models.DateTimeField(null=True, blank=True)
    manager_approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='nhis_manager_approvals')

    # Rejection tracking
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='nhis_rejections')
    rejection_reason = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Generate form number if it doesn't exist
        if not self.form_number:
            from datetime import datetime
            year = datetime.now().year
            last_form = NHISForm.objects.filter(form_number__startswith=f'NHIS-{year}').order_by('-form_number').first()
            if last_form:
                try:
                    last_number = int(last_form.form_number.split('-')[-1])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            self.form_number = f'NHIS-{year}-{new_number:03d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"NHIS Form {self.form_number}" if self.form_number else f"NHIS Form {self.id}"


class NHISComment(models.Model):
    nhis_form = models.ForeignKey(NHISForm, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.nhis_form.form_number}"


class PTWComment(models.Model):
    ptw_form = models.ForeignKey(PTWForm, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.ptw_form.form_number}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('new_form', 'New Form Submission'),
        ('approved', 'Form Approved'),
        ('rejected', 'Form Rejected'),
        ('comment', 'New Comment'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    nhis_form = models.ForeignKey(NHISForm, on_delete=models.CASCADE, null=True, blank=True)
    ptw_form = models.ForeignKey(PTWForm, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message[:30]}..."
