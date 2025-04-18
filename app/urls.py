from django.urls import path
from . import views
from . import views_nhis
from . import views_ptw
from django.contrib.auth import views as auth_views

app_name = 'app'
urlpatterns = [
    path('', views.loginPage, name="login"),
    path('logout/', views.logoutUser, name="logout"),
    path('register/', views.registerPage, name="register"),
    path('reset_password/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('client/', views.clientDashboard, name="client"),
    path('supervisor/', views.supervisorDashboard, name="supervisor"),
    path('manager/', views.managerDashboard, name="manager"),
    path('createform/', views.create_ptw_form, name='create_form'),
    path('list/', views.form_list, name='form_list'),
    path('delete_form/<int:pk>/', views.delete_form, name='delete_form'),
    path('view_form/<int:pk>/', views.view_form, name='view_form'),
    path('approve/supervisor/<int:pk>/', views.approve_supervisor, name='approve_supervisor'),
    path('approve/manager/<int:pk>/', views.approve_manager, name='approve_manager'),
    path('disapprove-supervisor/<int:pk>/', views.disapprove_supervisor, name='disapprove_supervisor'),
    path('disapprove-manager/<int:pk>/', views.disapprove_manager, name='disapprove_manager'),
    path('edit_form/<int:pk>/', views.edit_form, name='edit_form'),
    # NHIS Form URLs
    path('create_nhis/', views_nhis.create_nhis_form, name='create_nhis'),
    path('nhis_list/', views_nhis.nhis_list, name='nhis_list'),
    path('nhis/<int:pk>/', views_nhis.nhis_detail, name='nhis_detail'),

    # PTW Form URLs
    path('create_ptw/', views_ptw.create_ptw_form, name='create_ptw'),
    path('ptw/<int:pk>/', views_ptw.ptw_detail, name='ptw_detail'),
    path('ptw_approve_supervisor/<int:pk>/', views_ptw.approve_ptw_supervisor, name='approve_ptw_supervisor'),
    path('ptw_reject_supervisor/<int:pk>/', views_ptw.reject_ptw_supervisor, name='reject_ptw_supervisor'),
    path('ptw_approve_manager/<int:pk>/', views_ptw.approve_ptw_manager, name='approve_ptw_manager'),
    path('ptw_reject_manager/<int:pk>/', views_ptw.reject_ptw_manager, name='reject_ptw_manager'),
    path('ptw_comment/<int:pk>/', views_ptw.ptw_comment, name='ptw_comment'),
    path('ptw_pdf/<int:pk>/', views_ptw.ptw_pdf, name='ptw_pdf'),
    path('edit_ptw_form/<int:pk>/', views_ptw.edit_ptw_form, name='edit_ptw_form'),
    path('delete_ptw_form/<int:pk>/', views_ptw.delete_ptw_form, name='delete_ptw_form'),
    path('nhis/edit/<int:pk>/', views_nhis.edit_nhis_form, name='edit_nhis_form'),
    path('nhis/delete/<int:pk>/', views_nhis.delete_nhis_form, name='delete_nhis_form'),
    path('nhis/approve/supervisor/<int:pk>/', views_nhis.approve_nhis_supervisor, name='approve_nhis_supervisor'),
    # Manager approval removed - supervisor is now the final approver
    # path('nhis/approve/manager/<int:pk>/', views_nhis.approve_nhis_manager, name='approve_nhis_manager'),
    path('nhis/reject/supervisor/<int:pk>/', views_nhis.reject_nhis_supervisor, name='reject_nhis_supervisor'),
    # Manager rejection removed - supervisor is now the final approver
    # path('nhis/reject/manager/<int:pk>/', views_nhis.reject_nhis_manager, name='reject_nhis_manager'),
    path('nhis/comment/<int:pk>/', views_nhis.add_nhis_comment, name='add_nhis_comment'),
    path('nhis/pdf/<int:pk>/', views_nhis.nhis_pdf, name='nhis_pdf'),

    # Notification URLs
    path('notifications/', views_nhis.notifications, name='notifications'),
    path('notifications/mark-read/<int:notification_id>/', views_nhis.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views_nhis.mark_all_notifications_read, name='mark_all_notifications_read'),

    # Dashboard
    path('dashboard/', views_nhis.dashboard, name='dashboard'),

    # Reports
    path('form-report/', views.form_report, name='form_report'),

]