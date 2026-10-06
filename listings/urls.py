from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('targets/add/', views.add_target_view, name='add_target'),
    path('targets/<int:target_id>/toggle/', views.toggle_target_view, name='toggle_target'),
    path('targets/<int:target_id>/delete/', views.delete_target_view, name='delete_target'),
    path('targets/<int:target_id>/scan/', views.scan_target_manual_view, name='scan_target'),
]
