from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('listings/', views.listing_list_view, name='listing_list'),
    path('listings/<int:listing_id>/', views.listing_detail_view, name='listing_detail'),
    path('recommendations/', views.recommendations_view, name='recommendations'),
    path('preference/new/', views.create_preference_view, name='create_preference'),
    path('api/listings/<int:listing_id>/favorite/', views.toggle_favorite_ajax_view, name='toggle_favorite_ajax'),
    path('api/chatbot/', views.chatbot_assistant_ajax_view, name='chatbot_assistant_ajax'),
]
