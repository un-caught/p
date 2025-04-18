import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum
from django.db import transaction # Import transaction
from .models import LeaveRequest, LeaveType, LeaveBalance, LeavePeriod # Import LeavePeriod
from .forms import LeaveRequestForm, LeaveApprovalForm, LeaveTypeForm, BaseLeavePeriodFormSet # Import BaseLeavePeriodFormSet
from app.decorators import allowed_users

# --- Helper Function ---
def calculate_leave_dates(start_date, duration):
    """
    Calculates the end date and resumption date for a leave period,
    skipping weekends (Saturday and Sunday).
    Duration is the number of working days.
    """
    if not isinstance(start_date, datetime.date) or not isinstance(duration, int) or duration <= 0:
        return None, None

    current_date = start_date
    days_added = 0
    while days_added < duration:
        # Skip weekends
        if current_date.weekday() < 5: # Monday=0, Tuesday=1, ..., Friday=4
            days_added += 1
        # If we haven't reached the full duration yet, move to the next day
        if days_added < duration:
             current_date += datetime.timedelta(days=1)
        # If we have reached the duration, current_date is the end_date
        # unless it landed on a weekend after incrementing, handle this edge case?
        # For simplicity, let's assume the loop condition handles it:
        # the last working day counted *is* the end date.

    end_date = current_date

    # Calculate resumption date (the next working day after end_date)
    resumption_date = end_date + datetime.timedelta(days=1)
    while resumption_date.weekday() >= 5: # Skip weekends
        resumption_date += datetime.timedelta(days=1)

    return end_date, resumption_date
# --- End Helper Function ---

@login_required(login_url='app:login')
def leave_dashboard(request):
    """Dashboard view for leave management"""
    # Get pending leave requests for supervisors and managers
    pending_requests = None
    if request.user.groups.filter(name__in=['supervisor', 'manager']).exists():
        pending_requests = LeaveRequest.objects.filter(status='pending').order_by('-created_at')
    
    # Get user's leave requests
    user_requests = LeaveRequest.objects.filter(user=request.user).order_by('-created_at')
    
    # Get user's leave balances for the current year
    current_year = timezone.now().year
    leave_balances = LeaveBalance.objects.filter(user=request.user, year=current_year)
    
    context = {
        'pending_requests': pending_requests,
        'user_requests': user_requests,
        'leave_balances': leave_balances,
    }
    return render(request, 'leave/dashboard.html', context)

@login_required(login_url='app:login')
def create_leave_request(request):
    """Create a new leave request with dynamic periods."""
    user = request.user
    current_year = timezone.now().year # Default active year

    # Calculate initial leave days used and outstanding for the default year
    # Sum durations from approved leave periods for the user in the current year
    approved_periods = LeavePeriod.objects.filter(
        leave_request__user=user,
        leave_request__status='approved',
        start_date__year=current_year # Consider filtering by active_year from form if needed
    )
    total_days_used = approved_periods.aggregate(total=Sum('duration'))['total'] or 0
    outstanding_days = 15 - total_days_used # Assuming 15 days allowance

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, request.FILES, user=user) # Pass user for filtering
        formset = BaseLeavePeriodFormSet(request.POST, prefix='periods')

        if form.is_valid() and formset.is_valid():
            
            # Recalculate outstanding based on selected year in form
            selected_year = int(form.cleaned_data.get('active_year', current_year))
            approved_periods_selected_year = LeavePeriod.objects.filter(
                leave_request__user=user,
                leave_request__status='approved',
                start_date__year=selected_year
            )
            current_total_days_used = approved_periods_selected_year.aggregate(total=Sum('duration'))['total'] or 0
            current_outstanding_days = 15 - current_total_days_used

            # Calculate total requested duration from the formset
            total_requested_duration = 0
            for period_form in formset.cleaned_data:
                 # Check if the form is not marked for deletion and has data
                if period_form and not period_form.get('DELETE', False):
                    duration = period_form.get('duration')
                    if duration:
                        total_requested_duration += duration

            if total_requested_duration <= 0:
                 messages.error(request, "You must add at least one leave period with a duration.")
                 # Re-render form with error (need context vars below)
            elif total_requested_duration > current_outstanding_days:
                messages.error(request, f"Requested duration ({total_requested_duration} days) exceeds your outstanding balance ({current_outstanding_days} days) for {selected_year}.")
                # Re-render form with error (need context vars below)
            else:
                try:
                    with transaction.atomic(): # Use a transaction
                        leave_request = form.save(commit=False)
                        leave_request.user = user
                        leave_request.save() # Save the main request first

                        # Link formset to the saved request and save periods
                        formset.instance = leave_request
                        
                        # Save new/updated periods and calculate dates
                        for period_form_data in formset.cleaned_data:
                            if period_form_data and not period_form_data.get('DELETE', False):
                                start_date = period_form_data.get('start_date')
                                duration = period_form_data.get('duration')
                                period_id = period_form_data.get('id') # Get ID if updating

                                if start_date and duration:
                                    end_date, resumption_date = calculate_leave_dates(start_date, duration)
                                    if end_date and resumption_date:
                                        # Get or create the period instance
                                        if period_id:
                                            period_instance = period_id # Already an instance from formset
                                        else: # Should not happen with inlineformset unless manually adding?
                                             # Let formset handle creation via save() below? Test this.
                                             # For now, assume formset handles linking via instance
                                             pass

                                        # Update calculated dates before formset save might be needed
                                        # Let's try saving the formset directly first
                                        # period_instance.end_date = end_date
                                        # period_instance.resumption_date = resumption_date
                                        # period_instance.save() # Save individual instance?

                        # Save the formset (handles create, update, delete)
                        formset.save() 

                        # Now update calculated dates for newly created/updated periods
                        for period in leave_request.periods.all():
                             if not period.end_date or not period.resumption_date: # Only calculate if not already set
                                 end_date_calc, resumption_date_calc = calculate_leave_dates(period.start_date, period.duration)
                                 if end_date_calc and resumption_date_calc:
                                     period.end_date = end_date_calc
                                     period.resumption_date = resumption_date_calc
                                     period.save(update_fields=['end_date', 'resumption_date'])


                        messages.success(request, "Leave request submitted successfully.")
                        return redirect('leave:dashboard')
                except Exception as e:
                     messages.error(request, f"An error occurred while saving: {e}")
                     # Re-render form with error (need context vars below)

        else: # Form or formset is invalid
            messages.error(request, "Please correct the errors below.")
            # Errors will be displayed by the template tags

    else: # GET request
        form = LeaveRequestForm(user=user) # Pass user for filtering dropdowns
        formset = BaseLeavePeriodFormSet(prefix='periods')

    context = {
        'form': form,
        'formset': formset,
        'total_days_used': total_days_used, # Pass calculated values
        'outstanding_days': outstanding_days,
    }
    return render(request, 'leave/create_request.html', context)

@login_required(login_url='app:login')
def view_leave_request(request, pk):
    """View details of a leave request"""
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    
    # Check if user is authorized to view this request
    is_owner = leave_request.user == request.user
    is_approver = request.user.groups.filter(name__in=['supervisor', 'manager']).exists()
    
    if not (is_owner or is_approver):
        messages.error(request, "You are not authorized to view this leave request.")
        return redirect('leave:dashboard')
    
    context = {
        'leave_request': leave_request,
        'is_approver': is_approver,
    }
    return render(request, 'leave/view_request.html', context)

@login_required(login_url='app:login')
@allowed_users(allowed_roles=['supervisor', 'manager'])
def approve_leave_request(request, pk):
    """Approve or reject a leave request"""
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    
    if leave_request.status != 'pending':
        messages.error(request, "This leave request has already been processed.")
        return redirect('leave:dashboard')
    
    if request.method == 'POST':
        form = LeaveApprovalForm(request.POST, instance=leave_request)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.approved_by = request.user
            leave_request.approved_date = timezone.now()
            leave_request.save()
            
            # If approved, update leave balance
            if leave_request.status == 'approved':
                current_year = timezone.now().year
                leave_balance, created = LeaveBalance.objects.get_or_create(
                    user=leave_request.user,
                    leave_type=leave_request.leave_type,
                    year=current_year,
                    defaults={'initial_balance': leave_request.leave_type.max_days}
                )
                
                leave_balance.used_days += leave_request.days_requested
                leave_balance.save()
                
                messages.success(request, "Leave request approved successfully.")
            else:
                messages.success(request, "Leave request rejected.")
            
            return redirect('leave:dashboard')
    else:
        form = LeaveApprovalForm(instance=leave_request)
    
    context = {
        'form': form,
        'leave_request': leave_request,
    }
    return render(request, 'leave/approve_request.html', context)

@login_required(login_url='app:login')
def cancel_leave_request(request, pk):
    """Cancel a pending leave request"""
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    
    # Only the owner can cancel their request
    if leave_request.user != request.user:
        messages.error(request, "You are not authorized to cancel this leave request.")
        return redirect('leave:dashboard')
    
    # Only pending requests can be cancelled
    if leave_request.status != 'pending':
        messages.error(request, "Only pending leave requests can be cancelled.")
        return redirect('leave:dashboard')
    
    if request.method == 'POST':
        leave_request.status = 'cancelled'
        leave_request.save()
        messages.success(request, "Leave request cancelled successfully.")
        return redirect('leave:dashboard')
    
    return render(request, 'leave/cancel_request.html', {'leave_request': leave_request})

@login_required(login_url='app:login')
@allowed_users(allowed_roles=['manager'])
def manage_leave_types(request):
    """View and manage leave types"""
    leave_types = LeaveType.objects.all()
    return render(request, 'leave/manage_types.html', {'leave_types': leave_types})

@login_required(login_url='app:login')
@allowed_users(allowed_roles=['manager'])
def create_leave_type(request):
    """Create a new leave type"""
    if request.method == 'POST':
        form = LeaveTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Leave type created successfully.")
            return redirect('leave:manage_types')
    else:
        form = LeaveTypeForm()
    
    return render(request, 'leave/create_type.html', {'form': form})

@login_required(login_url='app:login')
@allowed_users(allowed_roles=['manager'])
def edit_leave_type(request, pk):
    """Edit an existing leave type"""
    leave_type = get_object_or_404(LeaveType, pk=pk)
    
    if request.method == 'POST':
        form = LeaveTypeForm(request.POST, instance=leave_type)
        if form.is_valid():
            form.save()
            messages.success(request, "Leave type updated successfully.")
            return redirect('leave:manage_types')
    else:
        form = LeaveTypeForm(instance=leave_type)
    
    return render(request, 'leave/edit_type.html', {'form': form, 'leave_type': leave_type})

@login_required(login_url='app:login')
@allowed_users(allowed_roles=['manager'])
def delete_leave_type(request, pk):
    """Delete a leave type"""
    leave_type = get_object_or_404(LeaveType, pk=pk)
    
    if request.method == 'POST':
        leave_type.delete()
        messages.success(request, "Leave type deleted successfully.")
        return redirect('leave:manage_types')
    
    return render(request, 'leave/delete_type.html', {'leave_type': leave_type})

@login_required(login_url='app:login')
@allowed_users(allowed_roles=['manager'])
def manage_leave_balances(request):
    """View and manage leave balances for all users"""
    current_year = timezone.now().year
    leave_balances = LeaveBalance.objects.filter(year=current_year)
    
    return render(request, 'leave/manage_balances.html', {
        'leave_balances': leave_balances,
        'current_year': current_year,
    })
