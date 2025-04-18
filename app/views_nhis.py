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

from .models import NHISForm, NHISComment, Notification
from .forms import NHISSubmissionForm, CommentForm, RejectForm
from .decorators import allowed_users
from .utils import create_notification, send_form_notification_email
from .location_utils import map_form_location_to_member_location, validate_user_location_match


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['staff'])
def create_nhis_form(request):
    # Get user's location
    user_location = None
    try:
        user_member = request.user.member
        user_location = user_member.location
    except:
        pass

    if request.method == 'POST':
        form = NHISSubmissionForm(request.POST)
        if form.is_valid():
            # Check if the selected location matches the user's location
            selected_location = form.cleaned_data.get('location')
            if not validate_user_location_match(user_location, selected_location):
                # Location mismatch - show error
                messages.error(request, f"You can only create forms for your assigned location ({user_location}). Please select the correct location.")
                return render(request, 'nhis.html', {'form': form})

            # Save the form
            submission = form.save(commit=False)
            submission.user = request.user
            submission.save()
            form.save_m2m()

            # Get supervisors and managers
            supervisors = User.objects.filter(groups__name='supervisor')
            managers = User.objects.filter(groups__name='manager')

            # Get user's location
            user_location = None
            try:
                user_member = request.user.member
                user_location = user_member.location
            except:
                pass

            # Get form's location
            form_location = submission.location

            # Filter recipients by the form's location
            if form_location:
                # Now we can do an exact match since we're using standardized location choices
                supervisors = supervisors.filter(member__location=form_location)
                managers = managers.filter(member__location=form_location)

                print(f"Filtering for location: {form_location}")
                print(f"Found {supervisors.count()} supervisors and {managers.count()} managers")
            else:
                # If form has no location, fallback to user's location
                if user_location:
                    supervisors = supervisors.filter(member__location=user_location)
                    managers = managers.filter(member__location=user_location)
                else:
                    # If neither form nor user has a location, don't notify anyone
                    supervisors = User.objects.none()
                    managers = User.objects.none()
                    messages.warning(request, "Could not determine location to notify supervisors/managers.")

            # Create notifications for supervisors
            for supervisor in supervisors:
                create_notification(
                    recipient=supervisor,
                    sender=request.user,
                    notification_type='new_form',
                    nhis_form=submission,
                    message=f"New NHIS Form {submission.form_number} has been submitted by {request.user.get_full_name()} for review."
                )

            # Create notifications for managers
            for manager in managers:
                create_notification(
                    recipient=manager,
                    sender=request.user,
                    notification_type='new_form',
                    nhis_form=submission,
                    message=f"New NHIS Form {submission.form_number} has been submitted by {request.user.get_full_name()} for review."
                )

            # Send email notifications
            send_form_notification_email(
                submission,
                'new_form',
                list(supervisors) + list(managers)
            )

            messages.success(request, f"NHIR Form {submission.form_number} has been submitted successfully.")
            return redirect('app:nhis_list')
    else:
        form = NHISSubmissionForm()

    return render(request, 'nhis.html', {'form': form})


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['staff', 'supervisor', 'manager'])
def nhis_list(request):
    # Get search parameters
    form_number = request.GET.get('form_number', '')
    location_search = request.GET.get('location_search', '')
    status_search = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Start with all forms
    query = NHISForm.objects.all()

    # Apply filters
    if form_number:
        query = query.filter(form_number__icontains=form_number)
    if location_search:
        query = query.filter(location__icontains=location_search)
    if status_search:
        query = query.filter(status=status_search)
    if date_from:
        date_from_obj = parse_date(date_from)
        if date_from_obj:
            query = query.filter(date__gte=date_from_obj)
    if date_to:
        date_to_obj = parse_date(date_to)
        if date_to_obj:
            query = query.filter(date__lte=date_to_obj)

    # Get current user's location
    user_location = None
    try:
        user_member = request.user.member
        user_location = user_member.location
    except:
        pass # Handle cases where user might not have a Member profile or location

    # Filter based on user role and location
    if request.user.groups.filter(name='staff').exists():
        # Staff see their own submissions
        submissions = query.filter(user=request.user)
    elif request.user.groups.filter(name__in=['manager', 'supervisor']).exists():
        # Managers and Supervisors see forms submitted by users in their location
        if user_location:
            submissions = query.filter(user__member__location=user_location)
        else:
            # If manager/supervisor has no location, they see nothing for now
            submissions = NHISForm.objects.none()
            messages.warning(request, "Your location is not set. Cannot display forms.")
    else:
        # Other roles see nothing
        submissions = NHISForm.objects.none()

    context = {
        'submissions': submissions,
        'form_number': form_number,
        'location_search': location_search,
        'status_search': status_search,
        'date_from': date_from_obj if 'date_from_obj' in locals() else '',
        'date_to': date_to_obj if 'date_to_obj' in locals() else '',
    }

    return render(request, 'nhis_list.html', context)


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['staff', 'supervisor', 'manager'])
def nhis_detail(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)

    # Check if the user has permission to view this form
    if request.user.groups.filter(name='staff').exists() and request.user != submission.user:
        messages.error(request, "You don't have permission to view this form.")
        return redirect('app:nhis_list')

    # Mark related notifications as read
    Notification.objects.filter(
        recipient=request.user,
        nhis_form=submission,
        is_read=False
    ).update(is_read=True)

    return render(request, 'nhis_detail.html', {'submission': submission})


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['supervisor'])
def approve_nhis_supervisor(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid() and submission.status == 'awaiting_supervisor':
            # Save the comment if provided
            if comment_form.cleaned_data['comment']:
                comment = comment_form.save(commit=False)
                comment.nhis_form = submission
                comment.user = request.user
                comment.save()

                # Notify the staff about the comment
                create_notification(
                    recipient=submission.user,
                    sender=request.user,
                    notification_type='comment',
                    nhis_form=submission,
                    message=f"Supervisor {request.user.get_full_name()} commented on your NHIS Form {submission.form_number}."
                )

            # Update submission status - directly to approved
            submission.status = 'approved'
            submission.supervisor_approved_at = timezone.now()
            submission.supervisor_approved_by = request.user
            submission.save()

            # Notify the staff
            create_notification(
                recipient=submission.user,
                sender=request.user,
                notification_type='approved',
                nhis_form=submission,
                message=f"Your NHIS Form {submission.form_number} has been fully approved by supervisor {request.user.get_full_name()}."
            )

            # No need to notify managers anymore as supervisor is the final approver

            # Send email notification to the staff only
            send_form_notification_email(
                submission,
                'supervisor_approved',
                [submission.user]
            )

            messages.success(request, f"NHIS Form {submission.form_number} has been fully approved.")
            return redirect('app:nhis_list')
    else:
        comment_form = CommentForm()

    return render(request, 'nhis_approve.html', {
        'submission': submission,
        'comment_form': comment_form,
    })


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['supervisor'])
def reject_nhis_supervisor(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)

    if request.method == 'POST':
        reject_form = RejectForm(request.POST)
        if reject_form.is_valid() and submission.status == 'awaiting_supervisor':
            rejection_reason = reject_form.cleaned_data['rejection_reason']

            # Update submission status
            submission.status = 'rejected_by_supervisor'
            submission.rejected_at = timezone.now()
            submission.rejected_by = request.user
            submission.rejection_reason = rejection_reason
            submission.save()

            # Create a comment with the rejection reason
            NHISComment.objects.create(
                nhis_form=submission,
                user=request.user,
                comment=f"Form rejected: {rejection_reason}"
            )

            # Notify the staff
            create_notification(
                recipient=submission.user,
                sender=request.user,
                notification_type='rejected',
                nhis_form=submission,
                message=f"Your NHIS Form {submission.form_number} has been rejected by supervisor {request.user.get_full_name()}."
            )

            # Send email notification
            send_form_notification_email(
                submission,
                'supervisor_rejected',
                [submission.user]
            )

            messages.success(request, f"NHIS Form {submission.form_number} has been rejected.")
            return redirect('app:nhis_list')
    else:
        reject_form = RejectForm()

    return render(request, 'nhis_reject.html', {
        'submission': submission,
        'reject_form': reject_form,
    })


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['manager'])
def approve_nhis_manager(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid() and submission.status == 'awaiting_manager':
            # Save the comment if provided
            if comment_form.cleaned_data['comment']:
                comment = comment_form.save(commit=False)
                comment.nhis_form = submission
                comment.user = request.user
                comment.save()

                # Notify the staff about the comment
                create_notification(
                    recipient=submission.user,
                    sender=request.user,
                    notification_type='comment',
                    nhis_form=submission,
                    message=f"Manager {request.user.get_full_name()} commented on your NHIS Form {submission.form_number}."
                )

            # Update submission status
            submission.status = 'approved'
            submission.manager_approved_at = timezone.now()
            submission.manager_approved_by = request.user
            submission.save()

            # Notify the staff
            create_notification(
                recipient=submission.user,
                sender=request.user,
                notification_type='approved',
                nhis_form=submission,
                message=f"Your NHIS Form {submission.form_number} has been fully approved by manager {request.user.get_full_name()}."
            )

            # Get user's location
            user_location = None
            try:
                user_member = request.user.member
                user_location = user_member.location
            except:
                pass

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
            # Fallback to user's location
            elif user_location:
                supervisors = supervisors.filter(member__location=user_location)

            # Notify supervisors
            for supervisor in supervisors:
                create_notification(
                    recipient=supervisor,
                    sender=request.user,
                    notification_type='approved',
                    nhis_form=submission,
                    message=f"NHIS Form {submission.form_number} has been fully approved by manager {request.user.get_full_name()}."
                )

            # Send email notifications
            send_form_notification_email(
                submission,
                'manager_approved',
                [submission.user] + list(supervisors)
            )

            messages.success(request, f"NHIS Form {submission.form_number} has been fully approved.")
            return redirect('app:nhis_list')
    else:
        comment_form = CommentForm()

    return render(request, 'nhis_approve.html', {
        'submission': submission,
        'comment_form': comment_form,
    })


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['manager'])
def reject_nhis_manager(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)

    if request.method == 'POST':
        reject_form = RejectForm(request.POST)
        if reject_form.is_valid() and submission.status == 'awaiting_manager':
            rejection_reason = reject_form.cleaned_data['rejection_reason']

            # Update submission status
            submission.status = 'rejected_by_manager'
            submission.rejected_at = timezone.now()
            submission.rejected_by = request.user
            submission.rejection_reason = rejection_reason
            submission.save()

            # Create a comment with the rejection reason
            NHISComment.objects.create(
                nhis_form=submission,
                user=request.user,
                comment=f"Form rejected: {rejection_reason}"
            )

            # Notify the staff
            create_notification(
                recipient=submission.user,
                sender=request.user,
                notification_type='rejected',
                nhis_form=submission,
                message=f"Your NHIS Form {submission.form_number} has been rejected by manager {request.user.get_full_name()}."
            )

            # Get user's location
            user_location = None
            try:
                user_member = request.user.member
                user_location = user_member.location
            except:
                pass

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
            # Fallback to user's location
            elif user_location:
                supervisors = supervisors.filter(member__location=user_location)

            # Notify supervisors
            for supervisor in supervisors:
                create_notification(
                    recipient=supervisor,
                    sender=request.user,
                    notification_type='rejected',
                    nhis_form=submission,
                    message=f"NHIS Form {submission.form_number} has been rejected by manager {request.user.get_full_name()}."
                )

            # Send email notification
            send_form_notification_email(
                submission,
                'manager_rejected',
                [submission.user] + list(supervisors)
            )

            messages.success(request, f"NHIS Form {submission.form_number} has been rejected.")
            return redirect('app:nhis_list')
    else:
        reject_form = RejectForm()

    return render(request, 'nhis_reject.html', {
        'submission': submission,
        'reject_form': reject_form,
    })


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['staff', 'supervisor', 'manager'])
def add_nhis_comment(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.nhis_form = submission
            comment.user = request.user
            comment.save()

            # Determine who to notify
            recipients = []

            # Always notify the form creator
            if request.user != submission.user:
                recipients.append(submission.user)

            # Get user's location
            user_location = None
            try:
                user_member = request.user.member
                user_location = user_member.location
            except:
                pass

            # Get form's location
            form_location = submission.location

            # If staff is commenting, notify supervisors and managers
            if request.user.groups.filter(name='staff').exists():
                supervisors = User.objects.filter(groups__name='supervisor')
                managers = User.objects.filter(groups__name='manager')

                # Filter by form location if available
                if form_location:
                    # Now we can do an exact match since we're using standardized location choices
                    supervisors = supervisors.filter(member__location=form_location)
                    managers = managers.filter(member__location=form_location)

                    print(f"Filtering for location: {form_location}")
                    print(f"Found {supervisors.count()} supervisors and {managers.count()} managers")
                # Fallback to user's location
                elif user_location:
                    supervisors = supervisors.filter(member__location=user_location)
                    managers = managers.filter(member__location=user_location)

                recipients.extend(list(supervisors) + list(managers))

            # If supervisor is commenting, notify staff and managers
            elif request.user.groups.filter(name='supervisor').exists():
                managers = User.objects.filter(groups__name='manager')

                # Filter by form location if available
                if form_location:
                    # Now we can do an exact match since we're using standardized location choices
                    managers = managers.filter(member__location=form_location)

                    print(f"Filtering for location: {form_location}")
                    print(f"Found {managers.count()} managers")
                # Fallback to user's location
                elif user_location:
                    managers = managers.filter(member__location=user_location)

                recipients.extend(list(managers))

            # If manager is commenting, notify staff and supervisors
            elif request.user.groups.filter(name='manager').exists():
                supervisors = User.objects.filter(groups__name='supervisor')

                # Filter by form location if available
                if form_location:
                    # Now we can do an exact match since we're using standardized location choices
                    supervisors = supervisors.filter(member__location=form_location)

                    print(f"Filtering for location: {form_location}")
                    print(f"Found {supervisors.count()} supervisors")
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
                        nhis_form=submission,
                        message=f"{request.user.get_full_name()} commented on NHIS Form {submission.form_number}."
                    )

            # Send email notifications

            send_form_notification_email(
                submission,
                'new_comment',
                recipients
            )

            messages.success(request, "Your comment has been added successfully.")

            # Redirect back to the form detail page
            return redirect('app:nhis_detail', pk=submission.pk)
    else:
        comment_form = CommentForm()

    return render(request, 'nhis_comment.html', {
        'submission': submission,
        'comment_form': comment_form,
    })


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['staff', 'supervisor', 'manager'])
def nhis_pdf(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)

    # Check if the user has permission to view this form
    if request.user.groups.filter(name='staff').exists() and request.user != submission.user:
        messages.error(request, "You don't have permission to export this form.")
        return redirect('app:nhis_list')

    # Check if WeasyPrint is available
    if not WEASYPRINT_AVAILABLE:
        messages.error(request, "PDF export is not available. Please contact the administrator.")
        return redirect('app:nhis_detail', pk=submission.pk)

    # Prepare context for the PDF template
    context = {
        'submission': submission,
        'logo_path': os.path.join(settings.STATIC_ROOT, 'img', 'falcon.png'),
        'current_date': timezone.now(),
    }

    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_file:
        temp_html_path = temp_file.name

        # Render the HTML template to the temporary file
        html_content = render(request, 'nhis_pdf.html', context).content.decode('utf-8')
        temp_file.write(html_content.encode('utf-8'))

    try:
        # Since WeasyPrint is not available, just render the HTML
        with open(temp_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Create HTTP response with HTML
        response = HttpResponse(html_content, content_type='text/html')
        response['Content-Disposition'] = f'inline; filename="NHIS_Form_{submission.form_number}.html"'

        return response
    except Exception as e:
        messages.error(request, f"Error generating PDF: {e}")
        return redirect('app:nhis_detail', pk=submission.pk)
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_html_path):
            os.unlink(temp_html_path)


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['staff'])
def edit_nhis_form(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)

    # Check if the user has permission to edit this form
    if request.user != submission.user:
        messages.error(request, "You don't have permission to edit this form.")
        return redirect('app:nhis_list')

    # Check if the form is in a state that can be edited
    if submission.status not in ['rejected_by_supervisor', 'rejected_by_manager']:
        messages.error(request, "This form cannot be edited in its current state.")
        return redirect('app:nhis_detail', pk=submission.pk)

    # Get user's location
    user_location = None
    try:
        user_member = request.user.member
        user_location = user_member.location
    except:
        pass

    if request.method == 'POST':
        form = NHISSubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            # Check if the selected location matches the user's location
            selected_location = form.cleaned_data.get('location')
            if not validate_user_location_match(user_location, selected_location):
                # Location mismatch - show error
                messages.error(request, f"You can only create forms for your assigned location ({user_location}). Please select the correct location.")
                return render(request, 'edit_nhis_form.html', {'form': form, 'submission': submission})
            # Reset approval/rejection fields
            submission = form.save(commit=False)
            submission.status = 'awaiting_supervisor'
            submission.supervisor_approved_at = None
            submission.supervisor_approved_by = None
            # Keep manager fields for backward compatibility
            submission.manager_approved_at = None
            submission.manager_approved_by = None
            submission.rejected_at = None
            submission.rejected_by = None
            submission.rejection_reason = None
            submission.save()
            form.save_m2m()

            # Add a comment about the resubmission
            NHISComment.objects.create(
                nhis_form=submission,
                user=request.user,
                comment="Form has been edited and resubmitted."
            )

            # Get user's location
            user_location = None
            try:
                user_member = request.user.member
                user_location = user_member.location
            except:
                pass

            # Get form's location
            form_location = submission.location

            # Get supervisors and managers
            supervisors = User.objects.filter(groups__name='supervisor')
            managers = User.objects.filter(groups__name='manager')

            # Filter by form location if available
            if form_location:
                # Now we can do an exact match since we're using standardized location choices
                supervisors = supervisors.filter(member__location=form_location)
                managers = managers.filter(member__location=form_location)

                print(f"Filtering for location: {form_location}")
                print(f"Found {supervisors.count()} supervisors and {managers.count()} managers")
            # Fallback to user's location
            elif user_location:
                supervisors = supervisors.filter(member__location=user_location)
                managers = managers.filter(member__location=user_location)

            # Create notifications for supervisors
            for supervisor in supervisors:
                create_notification(
                    recipient=supervisor,
                    sender=request.user,
                    notification_type='new_form',
                    nhis_form=submission,
                    message=f"NHIS Form {submission.form_number} has been edited and resubmitted by {request.user.get_full_name()}."
                )

            # Create notifications for managers
            for manager in managers:
                create_notification(
                    recipient=manager,
                    sender=request.user,
                    notification_type='new_form',
                    nhis_form=submission,
                    message=f"NHIS Form {submission.form_number} has been edited and resubmitted by {request.user.get_full_name()}."
                )

            # Send email notifications
            send_form_notification_email(
                submission,
                'new_form',
                list(supervisors) + list(managers)
            )

            messages.success(request, f"NHIS Form {submission.form_number} has been updated and resubmitted.")
            return redirect('app:nhis_list')
    else:
        form = NHISSubmissionForm(instance=submission)

    return render(request, 'edit_nhis_form.html', {
        'form': form,
        'submission': submission,
    })


@login_required(login_url='app:login')
@allowed_users(allowed_roles=['staff'])
def delete_nhis_form(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)

    # Check if the user has permission to delete this form
    if request.user != submission.user:
        messages.error(request, "You don't have permission to delete this form.")
        return redirect('app:nhis_list')

    # Check if the form is in a state that can be deleted
    if submission.status != 'awaiting_supervisor':
        messages.error(request, "This form cannot be deleted in its current state.")
        return redirect('app:nhis_detail', pk=submission.pk)

    # Delete related notifications
    Notification.objects.filter(nhis_form=submission).delete()

    # Delete the form
    form_number = submission.form_number
    submission.delete()

    messages.success(request, f"NHIS Form {form_number} has been deleted.")
    return redirect('app:nhis_list')


@login_required(login_url='app:login')
def notifications(request):
    user_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    unread_count = user_notifications.filter(is_read=False).count()

    # Check if JSON format is requested
    if request.GET.get('format') == 'json':
        # Return JSON response with notification data
        return JsonResponse({
            'unread_count': unread_count,
            'total_count': user_notifications.count(),
            'notifications': [
                {
                    'id': notification.id,
                    'message': notification.message,
                    'type': notification.notification_type,
                    'is_read': notification.is_read,
                    'created_at': notification.created_at.isoformat(),
                    'form_id': notification.nhis_form.id if notification.nhis_form else (notification.ptw_form.id if notification.ptw_form else None),
                    'form_type': 'nhis' if notification.nhis_form else ('ptw' if notification.ptw_form else None)
                }
                for notification in user_notifications[:5]
            ]
        })

    # Otherwise render the HTML template
    return render(request, 'notifications.html', {
        'notifications': user_notifications,
        'unread_count': unread_count
    })


@login_required(login_url='app:login')
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()

    # Redirect to the form if it exists
    if notification.nhis_form:
        return redirect('app:nhis_detail', pk=notification.nhis_form.id)
    elif notification.ptw_form:
        return redirect('app:ptw_detail', pk=notification.ptw_form.id)

    # Otherwise, redirect back to notifications
    return redirect('app:notifications')


@login_required(login_url='app:login')
def mark_all_notifications_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('app:notifications')


@login_required(login_url='app:login')
def dashboard(request):
    # Get pending notifications count
    unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    # Get pending forms requiring attention
    pending_forms = []

    # For staff, show their rejected forms
    if request.user.groups.filter(name='staff').exists():
        rejected_forms = NHISForm.objects.filter(
            user=request.user,
            status__in=['rejected_by_supervisor', 'rejected_by_manager']
        ).order_by('-rejected_at')[:5]

        pending_forms = [
            {
                'form_number': form.form_number,
                'status': form.get_status_display(),
                'date': form.rejected_at,
                'url': f'/nhis/{form.pk}/',
                'type': 'danger'
            }
            for form in rejected_forms
        ]

    # For supervisors, show forms awaiting their approval
    elif request.user.groups.filter(name='supervisor').exists():
        awaiting_forms = NHISForm.objects.filter(
            status='awaiting_supervisor'
        ).order_by('-date')[:5]

        pending_forms = [
            {
                'form_number': form.form_number,
                'submitter': form.user.get_full_name(),
                'date': form.date,
                'url': f'/nhis/{form.pk}/',
                'type': 'warning'
            }
            for form in awaiting_forms
        ]

    # For managers, show forms awaiting their approval
    elif request.user.groups.filter(name='manager').exists():
        awaiting_forms = NHISForm.objects.filter(
            status='awaiting_manager'
        ).order_by('-date')[:5]

        pending_forms = [
            {
                'form_number': form.form_number,
                'submitter': form.user.get_full_name(),
                'date': form.date,
                'url': f'/nhis/{form.pk}/',
                'type': 'info'
            }
            for form in awaiting_forms
        ]

    # Get recent notifications
    recent_notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:5]

    context = {
        'unread_notifications_count': unread_notifications_count,
        'pending_forms': pending_forms,
        'recent_notifications': recent_notifications,
    }

    return render(request, 'dashboard.html', context)
