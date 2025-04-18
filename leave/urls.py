from django.urls import path
from . import views

app_name = 'leave'

urlpatterns = [
    path('', views.leave_dashboard, name='dashboard'),
    path('request/create/', views.create_leave_request, name='create_request'),
    path('request/<int:pk>/', views.view_leave_request, name='view_request'),
    path('request/<int:pk>/approve/', views.approve_leave_request, name='approve_request'),
    path('request/<int:pk>/cancel/', views.cancel_leave_request, name='cancel_request'),
    path('types/', views.manage_leave_types, name='manage_types'),
    path('types/create/', views.create_leave_type, name='create_type'),
    path('types/<int:pk>/edit/', views.edit_leave_type, name='edit_type'),
    path('types/<int:pk>/delete/', views.delete_leave_type, name='delete_type'),
    path('balances/', views.manage_leave_balances, name='manage_balances'),
]
