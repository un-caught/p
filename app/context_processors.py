from django.contrib.auth.models import Group
from app.models import PTWForm, NHISForm, Notification

def user_groups(request):
    # Ensure the user is authenticated before querying the database
    if request.user.is_authenticated:
        # Count of 'approved' PTWForms created by the logged-in user
        approved_count = PTWForm.objects.filter(status='approved', user=request.user).count()
        open_count = NHISForm.objects.filter(status__in=['awaiting_supervisor', 'awaiting_manager'], user=request.user).count()
        closed_count = NHISForm.objects.filter(status='closed', user=request.user).count()

        #  supervisor page
        total_ptw = PTWForm.objects.all().count()
        total_nhis = NHISForm.objects.all().count()
        approved_ptw = PTWForm.objects.filter(status='approved').count()
        closed_nhis = NHISForm.objects.filter(status='closed').count()
        disapproved_ptw = PTWForm.objects.filter(status='disapproved').count()
        denied_nhis = NHISForm.objects.filter(status='denied').count()
        pending_ptw = PTWForm.objects.filter(status__in=['awaiting_supervisor', 'awaiting_manager']).count()
        pending_nhis = NHISForm.objects.filter(status__in=['awaiting_supervisor', 'awaiting_manager']).count()


        # mannager
        pending_ptw_manager = PTWForm.objects.filter(status='awaiting_manager').count()
        pending_nhis_manager = NHISForm.objects.filter(status='awaiting_manager').count()


        # Count of 'pending' or other similar statuses for the logged-in user
        pend_count = PTWForm.objects.filter(
            status__in=['awaiting_supervisor', 'awaiting_manager'],
            user=request.user
        ).count()

        # Group checks
        is_supervisor = request.user.groups.filter(name="supervisor").exists()
        is_manager = request.user.groups.filter(name="manager").exists()
        is_staff = request.user.groups.filter(name="staff").exists()
        is_vendor = request.user.groups.filter(name="vendor").exists()
    else:
        # For unauthenticated users, return default values
        approved_count = 0
        open_count = 0
        closed_count = 0
        pend_count = 0
        is_staff = False
        is_vendor = False
        is_supervisor = False
        is_manager = False
        total_ptw = 0
        total_nhis = 0
        approved_ptw = 0
        closed_nhis = 0
        disapproved_ptw = 0
        denied_nhis = 0
        pending_ptw = 0
        pending_nhis = 0
        pending_ptw_manager = 0
        pending_nhis_manager = 0

    # Return the context dictionary
    return {
        'is_staff': is_staff,
        'is_vendor': is_vendor,
        'is_supervisor': is_supervisor,
        'is_manager': is_manager,
        'approved_count': approved_count,
        'pend_count': pend_count,
        'open_count': open_count,
        'closed_count': closed_count,
        'total_ptw': total_ptw,
        'total_nhis': total_nhis,
        'approved_ptw': approved_ptw,
        'closed_nhis': closed_nhis,
        'disapproved_ptw': disapproved_ptw,
        'denied_nhis': denied_nhis,
        'pending_ptw': pending_ptw,
        'pending_nhis': pending_nhis,
        'pending_ptw_manager': pending_ptw_manager,
        'pending_nhis_manager': pending_nhis_manager,
    }

def notification_count(request):
    """
    Context processor to add unread notification count to all templates
    """
    if request.user.is_authenticated:
        try:
            unread_notifications_count = Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()

            recent_notifications = Notification.objects.filter(
                recipient=request.user
            ).order_by('-created_at')[:5]

            return {
                'unread_notifications_count': unread_notifications_count,
                'recent_notifications': recent_notifications,
            }
        except Exception as e:
            # If Notification model doesn't exist yet (e.g., before migrations)
            print(f"Error in notification_count context processor: {e}")
            return {
                'unread_notifications_count': 0,
                'recent_notifications': [],
            }
    return {
        'unread_notifications_count': 0,
        'recent_notifications': [],
    }