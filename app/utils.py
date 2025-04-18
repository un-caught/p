from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Notification, User

def create_notification(recipient, sender, notification_type, message, nhis_form=None, ptw_form=None):
    """Create a notification for a user"""
    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        nhis_form=nhis_form,
        ptw_form=ptw_form,
        message=message
    )
    return notification

def send_form_notification_email(form, notification_type, recipients):
    """
    Send email notifications about a form to multiple recipients

    Parameters:
    - form: The form instance (NHISForm or PTWForm)
    - notification_type: Type of notification (new_form, supervisor_approved, etc.)
    - recipients: List of User objects to receive the notification
    """
    # Determine form type
    form_type = 'NHIS' if hasattr(form, 'hazard') else 'PTW'

    subject_map = {
        'new_form': f"New {form_type} Form {form.form_number} Submitted",
        'supervisor_approved': f"{form_type} Form {form.form_number} Approved by Supervisor",
        'manager_approved': f"{form_type} Form {form.form_number} Fully Approved",
        'supervisor_rejected': f"{form_type} Form {form.form_number} Rejected by Supervisor",
        'manager_rejected': f"{form_type} Form {form.form_number} Rejected by Manager",
        'new_comment': f"New Comment on {form_type} Form {form.form_number}",
    }

    template_map = {
        'new_form': 'email/new_form_email.html',
        'supervisor_approved': 'email/supervisor_approved_email.html',
        'manager_approved': 'email/manager_approved_email.html',
        'supervisor_rejected': 'email/supervisor_rejected_email.html',
        'manager_rejected': 'email/manager_rejected_email.html',
        'new_comment': 'email/new_comment_email.html',
    }

    # Add form type to context
    context = {
        'form': form,
        'form_type': form_type,
        'form_number': form.form_number,
        'user_name': form.user.get_full_name() if form.user else 'Unknown',
        'location': form.location,
        'date': form.date_submitted,
        'status': form.get_status_display(),
    }

    subject = subject_map.get(notification_type, f"{form_type} Form {form.form_number} Update")
    template = template_map.get(notification_type, 'email/default_email.html')

    # Common context for all email templates
    context = {
        'form': form,
        'form_type': form_type,
        'form_number': form.form_number,
        'submitter': form.user.get_full_name() if form.user else "Unknown",
        'location': form.location,
    }

    # Add form-specific fields
    if form_type == 'NHIS':
        context['date'] = form.date
        context['observation'] = form.observation
    else:  # PTW form
        context['date'] = form.date_submitted
        context['work_description'] = form.work_description

    # Add specific context based on notification type
    if notification_type == 'supervisor_approved':
        context['approver'] = form.supervisor_approved_by.get_full_name() if form.supervisor_approved_by else "Unknown"
        context['approval_date'] = form.supervisor_approved_at
    elif notification_type == 'manager_approved':
        context['approver'] = form.manager_approved_by.get_full_name() if form.manager_approved_by else "Unknown"
        context['approval_date'] = form.manager_approved_at
    elif notification_type in ['supervisor_rejected', 'manager_rejected']:
        context['rejector'] = form.rejected_by.get_full_name() if form.rejected_by else "Unknown"
        context['rejection_date'] = form.rejected_at
        context['rejection_reason'] = form.rejection_reason

    # Get recipient emails
    recipient_emails = [user.email for user in recipients if user.email]

    if recipient_emails:
        try:
            # Render HTML content
            html_message = render_to_string(template, context)
            # Create plain text version
            plain_message = strip_tags(html_message)

            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=recipient_emails,
                html_message=html_message,
                fail_silently=True,  # Changed to True to prevent form submission errors
            )
            return True
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False
    return False

def get_unread_notifications_count(user):
    """Get the count of unread notifications for a user"""
    return Notification.objects.filter(recipient=user, is_read=False).count()

def get_recent_notifications(user, limit=5):
    """Get recent notifications for a user"""
    return Notification.objects.filter(recipient=user).order_by('-created_at')[:limit]

def mark_notification_as_read(notification_id):
    """Mark a notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id)
        notification.is_read = True
        notification.save()
        return True
    except Notification.DoesNotExist:
        return False

def mark_all_notifications_as_read(user):
    """Mark all notifications for a user as read"""
    Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
    return True
