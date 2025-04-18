from django.contrib import admin
from .models import LeaveType, LeaveRequest, LeaveBalance, LeavePeriod # Import LeavePeriod

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_days', 'description')
    search_fields = ('name',)

# --- Removed duplicate LeaveType registration ---

# Inline admin for Leave Periods within Leave Request
class LeavePeriodInline(admin.TabularInline):
    model = LeavePeriod
    fields = ('start_date', 'duration', 'end_date', 'resumption_date')
    readonly_fields = ('end_date', 'resumption_date') # Calculated fields
    extra = 0 # Don't show extra empty forms by default

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'leave_type', 'status', 'relief_officer', 'hod_line_manager', 'created_at') # Removed start/end date, added new fields
    list_filter = ('status', 'leave_type', 'created_at') # Removed start_date
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'reason')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [LeavePeriodInline] # Add the inline for periods

    fieldsets = (
        ('Request Information', {
            'fields': ('user', 'leave_type', 'reason', 'address', 'phone_number', 'attachment', 'status') # Removed start/end date, added new fields
        }),
         ('Assignment', {
            'fields': ('relief_officer', 'hod_line_manager')
        }),
        ('Approval Information', {
            'fields': ('approved_by', 'approved_date', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'leave_type', 'year', 'initial_balance', 'used_days', 'remaining_days')
    list_filter = ('year', 'leave_type')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
