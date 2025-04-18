from django.conf import settings # Import settings
from django.db import models
from django.contrib.auth.models import User

class LeaveType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    max_days = models.PositiveIntegerField(default=0)  # Maximum allowed days per year
    
    def __str__(self):
        return self.name

class LeaveRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    # start_date and end_date removed, handled by LeavePeriod now
    reason = models.TextField() # Relabeled as 'Purpose' in the form
    address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=16, null=True, blank=True)
    attachment = models.FileField(upload_to='leave_attachments/', null=True, blank=True)
    relief_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name='relief_assignments', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    hod_line_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name='hod_approvals', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Approval information
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_leaves'
    )
    approved_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.leave_type.name} ({self.start_date} to {self.end_date})"
    
    @property
    def days_requested(self):
        """Calculate the number of days requested"""
        delta = self.end_date - self.start_date
        return delta.days + 1  # Include both start and end dates

class LeaveBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    initial_balance = models.PositiveIntegerField(default=0)
    used_days = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('user', 'leave_type', 'year')
    
    def __str__(self):
        return f"{self.user.username} - {self.leave_type.name} ({self.year})"
    
    @property
    def remaining_days(self):
        """Calculate remaining leave days"""
        return self.initial_balance - self.used_days


# New model to handle multiple start/duration periods per request
class LeavePeriod(models.Model):
    leave_request = models.ForeignKey(LeaveRequest, related_name='periods', on_delete=models.CASCADE)
    start_date = models.DateField()
    duration = models.PositiveIntegerField() # Number of working days
    end_date = models.DateField() # Calculated based on start_date and duration (excluding weekends)
    resumption_date = models.DateField() # Calculated based on end_date

    def __str__(self):
        return f"{self.leave_request.id} - Period: {self.start_date} ({self.duration} days)"
