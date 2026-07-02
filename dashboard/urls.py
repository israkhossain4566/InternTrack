from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/api/', views.notifications_api, name='notifications_api'),
    path('notifications/<int:pk>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/read-all/', views.notification_mark_all_read, name='notification_mark_all_read'),
    path('notifications/<int:pk>/delete/', views.notification_delete, name='notification_delete'),
    path('admin-stats/', views.admin_stats, name='admin_stats'),
]
