from django.urls import path
from . import views

urlpatterns = [
    # Web Sayfaları
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('targets/add/', views.add_target_view, name='add_target'),
    path('targets/<int:target_id>/toggle/', views.toggle_target_view, name='toggle_target'),
    path('targets/<int:target_id>/delete/', views.delete_target_view, name='delete_target'),
    path('targets/<int:target_id>/scan/', views.scan_target_manual_view, name='scan_target'),

    # REST API & Cron Uç Noktaları (Mobil & Otomasyon)
    path('api/targets/', views.api_targets_view, name='api_targets'),
    path('api/listings/', views.api_listings_view, name='api_listings'),
    path('api/cron/scan/', views.api_cron_scan_view, name='api_cron_scan'),
]
