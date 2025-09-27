from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('events/', views.event_browse, name='event_browse'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:pk>/info/', views.event_info, name='event_info'),
    path('events/<int:pk>/agenda/', views.event_agenda, name='event_agenda'),
    path('events/<int:pk>/speakers/', views.event_speakers, name='event_speakers'),
    path('events/<int:pk>/maps/', views.event_maps, name='event_maps'),
]