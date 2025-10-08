from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import auth_views

app_name = 'api'

router = DefaultRouter()
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'sessions', views.SessionViewSet, basename='session')
router.register(r'registrations', views.RegistrationViewSet, basename='registration')
router.register(r'faqs', views.FAQViewSet, basename='faq')
router.register(r'contact-info', views.ContactInfoViewSet, basename='contactinfo')
router.register(r'app-content', views.AppContentViewSet, basename='appcontent')
router.register(r'announcements', views.AnnouncementViewSet, basename='announcement')
router.register(r'quick-actions', views.QuickActionViewSet, basename='quickaction')
router.register(r'supporting-materials', views.SupportingMaterialViewSet, basename='supportingmaterial')

urlpatterns = [
    # API routes
    path('', include(router.urls)),

    # Authentication API endpoints
    path('auth/login/', auth_views.login, name='api_login'),
    path('auth/register/', auth_views.register, name='api_register'),
    path('auth/external-register/', auth_views.external_register, name='api_external_register'),
    path('auth/logout/', auth_views.logout, name='api_logout'),
    path('auth/profile/', auth_views.profile, name='api_profile'),
    path('auth/change-password/', auth_views.change_password, name='api_change_password'),
    path('auth/announcements/', auth_views.announcements, name='api_announcements'),

    # App content endpoints
    path('app-content/<str:content_type>/', auth_views.app_content, name='api_app_content'),
    path('faqs/', auth_views.faqs, name='api_faqs'),
    path('contact-info/', auth_views.contact_info, name='api_contact_info'),
]