from .models import Notification, NHISForm, PTWForm
from django.contrib.auth.models import Group

class NotificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add notification count to request before view is called
        if request.user.is_authenticated:
            try:
                # Get unread notifications count
                unread_notifications_count = Notification.objects.filter(
                    recipient=request.user,
                    is_read=False
                ).count()

                # Get recent notifications (both read and unread)
                recent_notifications = Notification.objects.filter(
                    recipient=request.user
                ).order_by('-created_at')[:10]  # Increased from 5 to 10

                request.unread_notifications_count = unread_notifications_count
                request.recent_notifications = recent_notifications

                # Add pending forms based on user role
                pending_forms = []

                # For staff, show their rejected NHIS forms
                if request.user.groups.filter(name='staff').exists():
                    try:
                        rejected_forms = NHISForm.objects.filter(
                            user=request.user,
                            status__in=['rejected_by_supervisor', 'rejected_by_manager']
                        ).order_by('-rejected_at')[:5]

                        pending_forms = [
                            {
                                'form_number': form.form_number or f'NHIS-{form.id}',
                                'status': form.get_status_display(),
                                'date': form.rejected_at or form.date,
                                'url': f'/nhis/{form.pk}/',
                                'type': 'danger'
                            }
                            for form in rejected_forms
                        ]
                    except Exception as e:
                        print(f"Error getting staff pending NHIS forms: {e}")

                # For vendors, show their rejected PTW forms
                elif request.user.groups.filter(name='vendor').exists():
                    try:
                        rejected_forms = PTWForm.objects.filter(
                            user=request.user,
                            status__in=['rejected_by_supervisor', 'rejected_by_manager']
                        ).order_by('-rejected_at')[:5]

                        pending_forms = [
                            {
                                'form_number': form.form_number or f'PTW-{form.id}',
                                'status': form.get_status_display(),
                                'date': form.rejected_at or form.date_submitted,
                                'url': f'/ptw/{form.pk}/',
                                'type': 'danger'
                            }
                            for form in rejected_forms
                        ]
                    except Exception as e:
                        print(f"Error getting vendor pending PTW forms: {e}")

                # For supervisors, show forms awaiting their approval
                elif request.user.groups.filter(name='supervisor').exists():
                    try:
                        # Get user's location
                        user_location = None
                        try:
                            user_member = request.user.member
                            user_location = user_member.location
                        except:
                            pass

                        # Get NHIS forms awaiting supervisor approval
                        nhis_query = NHISForm.objects.filter(status='awaiting_supervisor')

                        # Filter by location if available
                        if user_location:
                            nhis_query = nhis_query.filter(location__icontains=user_location)

                        awaiting_nhis_forms = nhis_query.order_by('-date')[:3]

                        # Get PTW forms awaiting supervisor approval
                        ptw_query = PTWForm.objects.filter(status='awaiting_supervisor')

                        # Filter by location if available
                        if user_location:
                            ptw_query = ptw_query.filter(location__icontains=user_location)

                        awaiting_ptw_forms = ptw_query.order_by('-date_submitted')[:3]

                        # Create pending forms list for NHIS forms
                        pending_forms = [
                            {
                                'form_number': form.form_number or f'NHIS-{form.id}',
                                'submitter': form.user.get_full_name() if form.user else 'Unknown',
                                'date': form.date,
                                'url': f'/nhis/{form.pk}/',
                                'type': 'warning'
                            }
                            for form in awaiting_nhis_forms
                        ]

                        # Add PTW forms to the pending forms list
                        pending_forms.extend([
                            {
                                'form_number': form.form_number or f'PTW-{form.id}',
                                'submitter': form.user.get_full_name() if form.user else 'Unknown',
                                'date': form.date_submitted,
                                'url': f'/ptw/{form.pk}/',
                                'type': 'info'
                            }
                            for form in awaiting_ptw_forms
                        ])
                    except Exception as e:
                        print(f"Error getting supervisor pending forms: {e}")

                # For managers, show forms awaiting their approval
                elif request.user.groups.filter(name='manager').exists():
                    try:
                        # Get user's location
                        user_location = None
                        try:
                            user_member = request.user.member
                            user_location = user_member.location
                        except:
                            pass

                        # Get NHIS forms awaiting manager approval
                        nhis_query = NHISForm.objects.filter(status='awaiting_manager')

                        # Filter by location if available
                        if user_location:
                            nhis_query = nhis_query.filter(location__icontains=user_location)

                        awaiting_nhis_forms = nhis_query.order_by('-date')[:3]

                        # Get PTW forms awaiting manager approval
                        ptw_query = PTWForm.objects.filter(status='awaiting_manager')

                        # Filter by location if available
                        if user_location:
                            ptw_query = ptw_query.filter(location__icontains=user_location)

                        awaiting_ptw_forms = ptw_query.order_by('-date_submitted')[:3]

                        # Create pending forms list for NHIS forms
                        pending_forms = [
                            {
                                'form_number': form.form_number or f'NHIS-{form.id}',
                                'submitter': form.user.get_full_name() if form.user else 'Unknown',
                                'date': form.date,
                                'url': f'/nhis/{form.pk}/',
                                'type': 'warning'
                            }
                            for form in awaiting_nhis_forms
                        ]

                        # Add PTW forms to the pending forms list
                        pending_forms.extend([
                            {
                                'form_number': form.form_number or f'PTW-{form.id}',
                                'submitter': form.user.get_full_name() if form.user else 'Unknown',
                                'date': form.date_submitted,
                                'url': f'/ptw/{form.pk}/',
                                'type': 'info'
                            }
                            for form in awaiting_ptw_forms
                        ])
                    except Exception as e:
                        print(f"Error getting manager pending forms: {e}")

                request.pending_forms = pending_forms
            except Exception as e:
                # If models don't exist yet (e.g., before migrations)
                print(f"Error in NotificationMiddleware: {e}")
                request.unread_notifications_count = 0
                request.recent_notifications = []
                request.pending_forms = []
        else:
            request.unread_notifications_count = 0
            request.recent_notifications = []
            request.pending_forms = []

        response = self.get_response(request)
        return response
