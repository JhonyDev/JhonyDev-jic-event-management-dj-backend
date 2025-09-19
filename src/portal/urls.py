from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Event Management
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:pk>/edit/', views.event_update, name='event_update'),
    path('events/<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('events/<int:pk>/register/', views.register_for_event, name='register_for_event'),
    path('events/<int:pk>/unregister/', views.unregister_from_event, name='unregister_from_event'),

    # Registrations
    path('my-registrations/', views.my_registrations, name='my_registrations'),
]