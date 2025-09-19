from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('events/', views.event_browse, name='event_browse'),
]