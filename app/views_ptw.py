from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.utils.dateparse import parse_date
from django.conf import settings
import os
import tempfile

# WeasyPrint is not available
WEASYPRINT_AVAILABLE = False

from .models import PTWForm, PTWComment, Notification
from .forms import PTWSubmissionForm, PTWCommentForm, PTWRejectForm
from .decorators import allowed_users
from .utils import create_notification, send_form_notification_email
from .location_utils import map_form_location_to_member_location, validate_user_location_match


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['vendor'])
def create_ptw_form(request):
    # Get user's location
    user_location = None
    try:
        user_member = request.user.member
        user_location = user_member.location
    except:
        pass

    if request.method == 'POST':
        form = PTWSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            # Check if the selected location matches the user's location
            selected_location = form.cleaned_data.get('location')
            if not validate_user_location_match(user_location, selected_location):
                # Location mismatch - show error
                messages.error(request, f"You can only create forms for your assigned location ({user_location}). Please select the correct location.")
                return render(request, 'ptw.html', {'form': form})

            # Save the form
            submission = form.save(commit=False)
            submission.user = request.user
            submission.save()
            form.save_m2m()

            # Get supervisors and managers in the same location as the vendor
            vendor_location = None
            try:
                vendor_member = request.user.member
                vendor_location = vendor_member.location
            except:
                pass

            # Get supervisors and managers
            supervisors = User.objects.filter(groups__name='supervisor')
            managers = User.objects.filter(groups__name='manager')

            # Filter recipients by the FORM's selected location
            form_location = submission.location # Now using standardized location choices
            if form_location:
                # Now we can do an exact match since we're using standardized location choices
                supervisors = supervisors.filter(member__location=form_location)
                managers = managers.filter(member__location=form_location)

                print(f"Filtering for location: {form_location}")
                print(f"Found {supervisors.count()} supervisors and {managers.count()} managers")
            else:
                # If form has no location selected, don't notify anyone based on location
                supervisors = User.objects.none()
                managers = User.objects.none()
                messages.warning(request, "Form location not specified. Cannot notify supervisors/managers based on location.")

            # Create notifications for supervisors
            for supervisor in supervisors:
                create_notification(
                    recipient=supervisor,
                    sender=request.user,
                    notification_type='new_form',
                    message=f"New PTW Form {submission.form_number} submitted by {request.user.get_full_name()} for {submission.location}.",
                    ptw_form=submission
                )

            # Create notifications for managers
            for manager in managers:
                create_notification(
                    recipient=manager,
                    sender=request.user,
                    notification_type='new_form',
                    message=f"New PTW Form {submission.form_number} submitted by {request.user.get_full_name()} for {submission.location}.",
                    ptw_form=submission
                )

            # Send email notifications
            send_form_notification_email(
                submission,
                'new_form',
                list(supervisors) + list(managers)
            )

            messages.success(request, f"PTW Form {submission.form_number} has been submitted successfully.")
            return redirect('app:form_list')
    else:
        form = PTWSubmissionForm()

    return render(request, 'ptw.html', {'form': form})


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['vendor', 'supervisor', 'manager'])
def form_list(request):
    # Get search parameters
    form_number = request.GET.get('form_number', '')
    location_search = request.GET.get('location_search', '')
    status_search = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Start with all forms
    query = PTWForm.objects.all()

    # Filter by form number if provided
    if form_number:
        query = query.filter(form_number__icontains=form_number)

    # Filter by location if provided
    if location_search:
        query = query.filter(location__icontains=location_search)

    # Filter by status if provided
    if status_search:
        query = query.filter(status=status_search)

    # Filter by date range if provided
    if date_from:
        try:
            date_from_obj = parse_date(date_from)
            if date_from_obj:
                query = query.filter(date_submitted__date__gte=date_from_obj)
        except:
            pass

    if date_to:
        try:
            date_to_obj = parse_date(date_to)
            if date_to_obj:
                query = query.filter(date_submitted__date__lte=date_to_obj)
        except:
            pass

    # Get user's location
    user_location = None
    try:
        user_member = request.user.member
        user_location = user_member.location
    except:
        pass

    # Filter based on user role and location
    if request.user.groups.filter(name='vendor').exists():
        # Vendors see their own submissions
        submissions = query.filter(user=request.user)
    elif request.user.groups.filter(name__in=['manager', 'supervisor']).exists():

        # Managers and Supervisors see forms submitted by vendors in their location
        if user_location:
            # Filter forms where the submitter's member location matches the viewer's location
            submissions = query.filter(
                user__member__isnull=False,  # Ensure submitter has a member profile
                user__member__location=user_location # Match viewer's location
            )
            # This relies on the submitter (user) having a related Member profile with the location set correctly.
        else:
            # If manager/supervisor has no location set, they see nothing
            submissions = PTWForm.objects.none()
            messages.warning(request, "Your location is not set. Cannot display forms based on location.")
    else:
        # Other roles see nothing
        submissions = PTWForm.objects.none()

    context = {
        'submissions': submissions,
        'form_number': form_number,
        'location_search': location_search,
        'status_search': status_search,
        'date_from': date_from_obj if 'date_from_obj' in locals() else '',
        'date_to': date_to_obj if 'date_to_obj' in locals() else '',
    }

    return render(request, 'form_list.html', context)


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['vendor', 'supervisor', 'manager'])
def ptw_detail(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)

    # Check if the user has permission to view this form
    if request.user.groups.filter(name='vendor').exists() and request.user != submission.user:
        messages.error(request, "You don't have permission to view this form.")
        return redirect('app:form_list')

    # Get user's location
    user_location = None
    try:
        user_member = request.user.member
        user_location = user_member.location
    except:
        pass

    # Check if supervisor/manager location matches the SUBMITTER's location
    if user_location and request.user.groups.filter(name__in=['supervisor', 'manager']).exists():
        submitter_location = None
        try:
            # Get the location directly from the submitter's Member profile
            submitter_location = submission.user.member.location
        except:
            # Handle cases where submitter might not have Member profile or location
            pass

        if user_location != submitter_location:
             messages.error(request, f"You ({user_location}) do not have permission to view forms submitted by users from other locations ({submitter_location}).")
             return redirect('app:form_list')

    # Mark related notifications as read
    Notification.objects.filter(
        recipient=request.user,
        ptw_form=submission,
        is_read=False
    ).update(is_read=True)

    return render(request, 'ptw_detail.html', {'submission': submission})


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['supervisor'])
def approve_ptw_supervisor(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)

    # Check if supervisor location matches the FORM's location
    user_location = None
    try:
        user_location = request.user.member.location
    except:
        pass # Handle if viewer has no member profile or location

    # Check if supervisor location matches the SUBMITTER's location
    submitter_location = None
    try:
        # Get the location directly from the submitter's Member profile
        submitter_location = submission.user.member.location
    except:
        # Handle cases where submitter might not have Member profile or location
        pass

    if user_location != submitter_location:
         messages.error(f"You ({user_location}) do not have permission to approve forms submitted by users from other locations ({submitter_location}).")
         return redirect('app:form_list')
    if request.method == 'POST':
        comment_form = PTWCommentForm(request.POST)
        if comment_form.is_valid() and submission.status == 'supervisor_signed':
            # Save the comment if provided
            if comment_form.cleaned_data['comment']:
                comment = comment_form.save(commit=False)
                comment.ptw_form = submission
                comment.user = request.user
                comment.save()

                # Notify the vendor about the comment
                create_notification(
                    recipient=submission.user,
                    sender=request.user,
                    notification_type='comment',
                    ptw_form=submission,
                    message=f"Supervisor {request.user.get_full_name()} commented on your PTW Form {submission.form_number}."
                )

            # Update submission status
            submission.status = 'awaiting_manager'
            submission.supervisor_approved_at = timezone.now()
            submission.supervisor_approved_by = request.user
            submission.save()

            # Notify the vendor
            create_notification(
                recipient=submission.user,
                sender=request.user,
                notification_type='approved',
                message=f"Your PTW Form {submission.form_number} has been approved by supervisor {request.user.get_full_name()} and is now awaiting manager approval.",
                ptw_form=submission
            )

            # Get form's location
            form_location = submission.location

            # Get managers in the same location
            managers = User.objects.filter(groups__name='manager')

            # Filter by form location if available
            if form_location:
                # Now we can do an exact match since we're using standardized location choices
                managers = managers.filter(member__location=form_location)

                print(f"Filtering for location: {form_location}")
                print(f"Found {managers.count()} managers")
            # Fallback to supervisor's location
            elif user_location:
                managers = managers.filter(member__location=user_location)

            # Notify managers
            for manager in managers:
                create_notification(
                    recipient=manager,
                    sender=request.user,
                    notification_type='approved',
                    message=f"PTW Form {submission.form_number} has been approved by supervisor {request.user.get_full_name()} and requires your approval.",
                    ptw_form=submission
                )

            # Send email notifications
            send_form_notification_email(
                submission,
                'supervisor_approved',
                [submission.user] + list(managers)
            )

            messages.success(request, f"PTW Form {submission.form_number} has been approved and sent to managers.")
            return redirect('app:form_list')
    else:
        comment_form = PTWCommentForm()

    return render(request, 'ptw_approve.html', {
        'submission': submission,
        'comment_form': comment_form,
    })


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['supervisor'])
def reject_ptw_supervisor(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)

    # Check if supervisor location matches the FORM's location
    user_location = None
    try:
        user_location = request.user.member.location
    except:
        pass # Handle if viewer has no member profile or location

    # Check if supervisor location matches the SUBMITTER's location
    submitter_location = None
    try:
        # Get the location directly from the submitter's Member profile
        submitter_location = submission.user.member.location
    except:
        # Handle cases where submitter might not have Member profile or location
        pass

    if user_location != submitter_location:
         messages.error(f"You ({user_location}) do not have permission to reject forms submitted by users from other locations ({submitter_location}).")
         return redirect('app:form_list')
    if request.method == 'POST':
        reject_form = PTWRejectForm(request.POST)
        if reject_form.is_valid() and submission.status in ['awaiting_supervisor', 'supervisor_signed']:
            rejection_reason = reject_form.cleaned_data['rejection_reason']

            # Update submission status
            submission.status = 'rejected_by_supervisor'
            submission.rejected_at = timezone.now()
            submission.rejected_by = request.user
            submission.rejection_reason = rejection_reason
            submission.save()

            # Create a comment with the rejection reason
            PTWComment.objects.create(
                ptw_form=submission,
                user=request.user,
                comment=f"Form rejected: {rejection_reason}"
            )

            # Notify the vendor
            create_notification(
                recipient=submission.user,
                sender=request.user,
                notification_type='rejected',
                message=f"Your PTW Form {submission.form_number} has been rejected by supervisor {request.user.get_full_name()}. Reason: {rejection_reason}",
                ptw_form=submission
            )

            # Send email notification
            send_form_notification_email(
                submission,
                'supervisor_rejected',
                [submission.user]
            )

            messages.success(request, f"PTW Form {submission.form_number} has been rejected.")
            return redirect('app:form_list')
    else:
        reject_form = PTWRejectForm()

    return render(request, 'ptw_reject.html', {
        'submission': submission,
        'reject_form': reject_form,
    })


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['manager'])
def approve_ptw_manager(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)

    # Check if manager location matches the FORM's location
    user_location = None
    try:
        user_location = request.user.member.location
    except:
        pass # Handle if viewer has no member profile or location

    # Check if manager location matches the SUBMITTER's location
    submitter_location = None
    try:
        # Get the location directly from the submitter's Member profile
        submitter_location = submission.user.member.location
    except:
        # Handle cases where submitter might not have Member profile or location
        pass

    if user_location != submitter_location:
         messages.error(f"You ({user_location}) do not have permission to approve forms submitted by users from other locations ({submitter_location}).")
         return redirect('app:form_list')
    if request.method == 'POST':
        comment_form = PTWCommentForm(request.POST)
        if comment_form.is_valid() and submission.status == 'manager_signed':
            # Save the comment if provided
            if comment_form.cleaned_data['comment']:
                comment = comment_form.save(commit=False)
                comment.ptw_form = submission
                comment.user = request.user
                comment.save()

                # Notify the vendor about the comment
                create_notification(
                    recipient=submission.user,
                    sender=request.user,
                    notification_type='comment',
                    message=f"Manager {request.user.get_full_name()} commented on your PTW Form {submission.form_number}.",
                    ptw_form=submission
                )

            # Update submission status
            submission.status = 'approved'
            submission.manager_approved_at = timezone.now()
            submission.manager_approved_by = request.user
            submission.save()

            # Notify the vendor
            create_notification(
                recipient=submission.user,
                sender=request.user,
                notification_type='approved',
                message=f"Your PTW Form {submission.form_number} has been fully approved by manager {request.user.get_full_name()}.",
                ptw_form=submission
            )

            # Get form's location
            form_location = submission.location

            # Get supervisors in the same location
            supervisors = User.objects.filter(groups__name='supervisor')

            # Filter by form location if available
            if form_location:
                # Map form location to member location
                member_location = map_form_location_to_member_location(form_location)

                if member_location:
                    supervisors = supervisors.filter(member__location=member_location)
            # Fallback to manager's location
            elif user_location:
                supervisors = supervisors.filter(member__location=user_location)

            # Notify supervisors
            for supervisor in supervisors:
                create_notification(
                    recipient=supervisor,
                    sender=request.user,
                    notification_type='approved',
                    message=f"PTW Form {submission.form_number} has been fully approved by manager {request.user.get_full_name()}.",
                    ptw_form=submission
                )

            # Send email notifications
            send_form_notification_email(
                submission,
                'manager_approved',
                [submission.user] + list(supervisors)
            )

            messages.success(request, f"PTW Form {submission.form_number} has been fully approved.")
            return redirect('app:form_list')
    else:
        comment_form = PTWCommentForm()

    return render(request, 'ptw_approve.html', {
        'submission': submission,
        'comment_form': comment_form,
    })


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['manager'])
def reject_ptw_manager(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)

    # Check if manager location matches the FORM's location
    user_location = None
    try:
        user_location = request.user.member.location
    except:
        pass # Handle if viewer has no member profile or location

    # Check if manager location matches the SUBMITTER's location
    submitter_location = None
    try:
        # Get the location directly from the submitter's Member profile
        submitter_location = submission.user.member.location
    except:
        # Handle cases where submitter might not have Member profile or location
        pass

    if user_location != submitter_location:
         messages.error(f"You ({user_location}) do not have permission to reject forms submitted by users from other locations ({submitter_location}).")
         return redirect('app:form_list')
    if request.method == 'POST':
        reject_form = PTWRejectForm(request.POST)
        if reject_form.is_valid() and submission.status in ['awaiting_manager', 'manager_signed']:
            rejection_reason = reject_form.cleaned_data['rejection_reason']

            # Update submission status
            submission.status = 'rejected_by_manager'
            submission.rejected_at = timezone.now()
            submission.rejected_by = request.user
            submission.rejection_reason = rejection_reason
            submission.save()

            # Create a comment with the rejection reason
            PTWComment.objects.create(
                ptw_form=submission,
                user=request.user,
                comment=f"Form rejected: {rejection_reason}"
            )

            # Notify the vendor
            create_notification(
                recipient=submission.user,
                sender=request.user,
                notification_type='rejected',
                message=f"Your PTW Form {submission.form_number} has been rejected by manager {request.user.get_full_name()}. Reason: {rejection_reason}",
                ptw_form=submission
            )

            # Send email notification
            send_form_notification_email(
                submission,
                'manager_rejected',
                [submission.user]
            )

            messages.success(request, f"PTW Form {submission.form_number} has been rejected.")
            return redirect('app:form_list')
    else:
        reject_form = PTWRejectForm()

    return render(request, 'ptw_reject.html', {
        'submission': submission,
        'reject_form': reject_form,
    })


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['vendor'])
def edit_ptw_form(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)

    # Check if the user has permission to edit this form
    if request.user != submission.user:
        messages.error(request, "You don't have permission to edit this form.")
        return redirect('app:form_list')

    # Check if the form is in a state that can be edited
    if submission.status not in ['rejected_by_supervisor', 'rejected_by_manager']:
        messages.error(request, "This form cannot be edited in its current state.")
        return redirect('app:ptw_detail', pk=submission.pk)

    # Get user's location
    user_location = None
    try:
        user_member = request.user.member
        user_location = user_member.location
    except:
        pass

    if request.method == 'POST':
        form = PTWSubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            # Check if the selected location matches the user's location
            selected_location = form.cleaned_data.get('location')
            if not validate_user_location_match(user_location, selected_location):
                # Location mismatch - show error
                messages.error(request, f"You can only create forms for your assigned location ({user_location}). Please select the correct location.")
                return render(request, 'edit_form.html', {'form': form, 'submission': submission})
            # Reset approval/rejection fields
            submission = form.save(commit=False)
            submission.status = 'awaiting_supervisor'
            submission.supervisor_approved_at = None
            submission.supervisor_approved_by = None
            submission.manager_approved_at = None
            submission.manager_approved_by = None
            submission.rejected_at = None
            submission.rejected_by = None
            submission.rejection_reason = None
            submission.save()
            form.save_m2m()

            # Add a comment about the resubmission
            PTWComment.objects.create(
                ptw_form=submission,
                user=request.user,
                comment="Form has been edited and resubmitted."
            )

            # Get form's location
            form_location = submission.location

            # Get user's location as fallback
            user_location = None
            try:
                user_member = request.user.member
                user_location = user_member.location
            except:
                pass

            # Get supervisors and managers in the same location
            supervisors = User.objects.filter(groups__name='supervisor')
            managers = User.objects.filter(groups__name='manager')

            # Filter by form location if available
            if form_location:
                # Now we can do an exact match since we're using standardized location choices
                supervisors = supervisors.filter(member__location=form_location)
                managers = managers.filter(member__location=form_location)

                print(f"Filtering for location: {form_location}")
                print(f"Found {supervisors.count()} supervisors and {managers.count()} managers")
            # Fallback to user's location if form location is not set
            elif user_location:
                supervisors = supervisors.filter(member__location=user_location)
                managers = managers.filter(member__location=user_location)

            # Notify supervisors
            for supervisor in supervisors:
                create_notification(
                    recipient=supervisor,
                    sender=request.user,
                    notification_type='new_form',
                    message=f"PTW Form {submission.form_number} has been edited and resubmitted by {request.user.get_full_name()}.",
                    ptw_form=submission
                )

            # Notify managers
            for manager in managers:
                create_notification(
                    recipient=manager,
                    sender=request.user,
                    notification_type='new_form',
                    message=f"PTW Form {submission.form_number} has been edited and resubmitted by {request.user.get_full_name()}.",
                    ptw_form=submission
                )

            # Send email notifications
            send_form_notification_email(
                submission,
                'new_form',
                list(supervisors) + list(managers)
            )

            messages.success(request, f"PTW Form {submission.form_number} has been updated and resubmitted.")
            return redirect('app:form_list')
    else:
        form = PTWSubmissionForm(instance=submission)

    return render(request, 'edit_form.html', {
        'form': form,
        'submission': submission,
    })


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['vendor'])
def delete_ptw_form(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)

    # Check if the user has permission to delete this form
    if request.user != submission.user:
        messages.error(request, "You don't have permission to delete this form.")
        return redirect('app:form_list')

    # Check if the form is in a state that can be deleted
    if submission.status != 'awaiting_supervisor':
        messages.error(request, "This form cannot be deleted in its current state.")
        return redirect('app:ptw_detail', pk=submission.pk)

    # Delete related notifications
    Notification.objects.filter(ptw_form=submission).delete()

    # Delete the form
    form_number = submission.form_number
    submission.delete()

    messages.success(request, f"PTW Form {form_number} has been deleted.")
    return redirect('app:form_list')


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['vendor', 'supervisor', 'manager'])
def ptw_comment(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)

    # Check if the user has permission to comment on this form
    if request.user.groups.filter(name='vendor').exists() and request.user != submission.user:
        messages.error(request, "You don't have permission to comment on this form.")
        return redirect('app:form_list')

    # Check if supervisor/manager location matches the FORM's location
    user_location = None
    try:
        user_location = request.user.member.location
    except:
        pass # Handle if viewer has no member profile or location

    if request.user.groups.filter(name__in=['supervisor', 'manager']).exists():
        # Check if supervisor/manager location matches the SUBMITTER's location
        submitter_location = None
        try:
            # Get the location directly from the submitter's Member profile
            submitter_location = submission.user.member.location
        except:
            # Handle cases where submitter might not have Member profile or location
            pass

        if user_location != submitter_location:
             messages.error(f"You ({user_location}) do not have permission to comment on forms submitted by users from other locations ({submitter_location}).")
             return redirect('app:form_list')
    if request.method == 'POST':
        comment_form = PTWCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.ptw_form = submission
            comment.user = request.user
            comment.save()

            # Determine who to notify
            recipients = []

            # Always notify the form creator
            if request.user != submission.user:
                recipients.append(submission.user)

            # Get form's location
            form_location = submission.location

            # If vendor is commenting, notify supervisors and managers
            if request.user.groups.filter(name='vendor').exists():
                supervisors = User.objects.filter(groups__name='supervisor')
                managers = User.objects.filter(groups__name='manager')

                # Filter by form location if available
                if form_location:
                    # Map form location to member location
                    member_location = map_form_location_to_member_location(form_location)

                    if member_location:
                        supervisors = supervisors.filter(member__location=member_location)
                        managers = managers.filter(member__location=member_location)
                # Fallback to user's location
                elif user_location:
                    supervisors = supervisors.filter(member__location=user_location)
                    managers = managers.filter(member__location=user_location)

                recipients.extend(list(supervisors) + list(managers))

            # If supervisor is commenting, notify managers
            elif request.user.groups.filter(name='supervisor').exists():
                managers = User.objects.filter(groups__name='manager')

                # Filter by form location if available
                if form_location:
                    # Map form location to member location
                    member_location = map_form_location_to_member_location(form_location)

                    if member_location:
                        managers = managers.filter(member__location=member_location)
                # Fallback to user's location
                elif user_location:
                    managers = managers.filter(member__location=user_location)

                recipients.extend(list(managers))

            # If manager is commenting, notify supervisors
            elif request.user.groups.filter(name='manager').exists():
                supervisors = User.objects.filter(groups__name='supervisor')

                # Filter by form location if available
                if form_location:
                    # Map form location to member location
                    member_location = map_form_location_to_member_location(form_location)

                    if member_location:
                        supervisors = supervisors.filter(member__location=member_location)
                # Fallback to user's location
                elif user_location:
                    supervisors = supervisors.filter(member__location=user_location)

                recipients.extend(list(supervisors))

            # Create notifications
            for recipient in recipients:
                if recipient != request.user:  # Don't notify yourself
                    create_notification(
                        recipient=recipient,
                        sender=request.user,
                        notification_type='comment',
                        message=f"{request.user.get_full_name()} commented on PTW Form {submission.form_number}.",
                        ptw_form=submission
                    )

            messages.success(request, "Your comment has been added.")
            return redirect('app:ptw_detail', pk=submission.pk)
    else:
        comment_form = PTWCommentForm()

    return render(request, 'ptw_comment.html', {
        'submission': submission,
        'comment_form': comment_form,
    })


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['vendor', 'supervisor', 'manager'])
def ptw_pdf(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)

    # Check if the user has permission to view this form
    if request.user.groups.filter(name='vendor').exists() and request.user != submission.user:
        messages.error(request, "You don't have permission to view this form.")
        return redirect('app:form_list')

    # Check if supervisor/manager is in the same location as the form
    user_location = None
    try:
        user_member = request.user.member
        user_location = user_member.location
    except:
        pass

    if user_location and (request.user.groups.filter(name='supervisor').exists() or request.user.groups.filter(name='manager').exists()):
        if user_location not in submission.location:
            messages.error(request, "You don't have permission to view forms from other locations.")
            return redirect('app:form_list')

    # If WeasyPrint is not available, render a template version
    if not WEASYPRINT_AVAILABLE:
        return render(request, 'ptw_pdf.html', {'submission': submission})

    # Generate PDF using WeasyPrint
    try:
        from weasyprint import HTML, CSS
        from django.template.loader import render_to_string
        from django.core.files.storage import default_storage

        # Render the template to a string
        html_string = render_to_string('ptw_pdf.html', {'submission': submission})

        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output:
            # Generate PDF
            HTML(string=html_string).write_pdf(output)

        # Read the temporary file
        with open(output.name, 'rb') as f:
            pdf = f.read()

        # Clean up the temporary file
        os.unlink(output.name)

        # Create the HTTP response
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="PTW_Form_{submission.form_number}.pdf"'
        return response

    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return render(request, 'ptw_pdf.html', {'submission': submission})
