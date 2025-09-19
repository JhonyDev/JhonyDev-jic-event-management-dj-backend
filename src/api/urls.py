from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import auth_views

app_name = 'api'

router = DefaultRouter()
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'registrations', views.RegistrationViewSet, basename='registration')

urlpatterns = [
    # API routes
    path('', include(router.urls)),

    # Authentication API endpoints
    path('auth/login/', auth_views.login, name='api_login'),
    path('auth/register/', auth_views.register, name='api_register'),
    path('auth/logout/', auth_views.logout, name='api_logout'),
]