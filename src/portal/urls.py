from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Event Management
    path('events/', views.event_list, name='event_list'),

    # All Items Navigation
    path('all-agendas/', views.all_agendas, name='all_agendas'),
    path('all-sessions/', views.all_sessions, name='all_sessions'),
    path('all-speakers/', views.all_speakers, name='all_speakers'),
    path('all-exhibitions/', views.all_exhibitions, name='all_exhibitions'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:pk>/edit/', views.event_update, name='event_update'),
    path('events/<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('events/<int:pk>/register/', views.register_for_event, name='register_for_event'),
    path('events/<int:pk>/unregister/', views.unregister_from_event, name='unregister_from_event'),
    path('events/<int:pk>/publish/', views.event_publish, name='event_publish'),
    path('events/<int:pk>/agenda-qr/', views.agenda_qr_code, name='agenda_qr_code'),
    path('events/<int:pk>/registration-qr/', views.registration_qr_code, name='registration_qr_code'),
    path('events/<int:pk>/registration-qr-display/', views.registration_qr_display, name='registration_qr_display'),

    # Attendees
    path('attendees/', views.attendees, name='attendees'),

    # Speaker Management
    path('events/<int:event_pk>/speakers/', views.speaker_list, name='speaker_list'),
    path('events/<int:event_pk>/speakers/add/', views.speaker_manage, name='speaker_manage'),
    path('events/<int:event_pk>/speakers/<int:speaker_pk>/edit/', views.speaker_manage, name='speaker_edit'),
    path('events/<int:event_pk>/speakers/<int:speaker_pk>/delete/', views.speaker_delete, name='speaker_delete'),

    # Agenda Management
    path('events/<int:event_pk>/agendas/', views.agenda_list, name='agenda_list'),
    path('events/<int:event_pk>/agendas/create/', views.agenda_manage, name='agenda_create'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/edit/', views.agenda_manage, name='agenda_edit'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/delete/', views.agenda_delete, name='agenda_delete'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/move-up/', views.agenda_move_up, name='agenda_move_up'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/move-down/', views.agenda_move_down, name='agenda_move_down'),
    path('events/<int:event_pk>/agendas/ajax-move/', views.agenda_move_ajax, name='agenda_move_ajax'),
    path('events/<int:event_pk>/agendas/partial/', views.agenda_partial, name='agenda_partial'),

    # Agenda Topic Management
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/topics/add/', views.agenda_topic_manage, name='agenda_topic_create'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/topics/<int:topic_pk>/edit/', views.agenda_topic_manage, name='agenda_topic_edit'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/topics/<int:topic_pk>/delete/', views.agenda_topic_delete, name='agenda_topic_delete'),

    # Agenda Coordinator Management
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/coordinators/add/', views.agenda_coordinator_manage, name='agenda_coordinator_create'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/coordinators/<int:coordinator_pk>/edit/', views.agenda_coordinator_manage, name='agenda_coordinator_edit'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/coordinators/<int:coordinator_pk>/delete/', views.agenda_coordinator_delete, name='agenda_coordinator_delete'),

    # Session/Agenda Management
    path('events/<int:event_pk>/sessions/', views.session_list, name='session_list'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/sessions/', views.session_list, name='agenda_session_list'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/sessions/create/', views.session_manage, name='session_create'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/sessions/<int:session_pk>/edit/', views.session_manage, name='session_edit'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/sessions/<int:session_pk>/delete/', views.session_delete, name='session_delete'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/sessions/<int:session_pk>/move-up/', views.session_move_up, name='session_move_up'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/sessions/<int:session_pk>/move-down/', views.session_move_down, name='session_move_down'),
    path('events/<int:event_pk>/sessions/ajax-move/', views.session_move_ajax, name='session_move_ajax'),


    # Exhibition Management
    path('events/<int:event_pk>/exhibition/', views.exhibition_areas, name='exhibition_areas'),
    path('events/<int:event_pk>/exhibition/create/', views.exhibition_area_create, name='exhibition_area_create'),
    path('events/<int:event_pk>/exhibition/<int:area_pk>/edit/', views.exhibition_area_create, name='exhibition_area_edit'),
    path('events/<int:event_pk>/exhibition/applications/', views.exhibitor_applications, name='exhibitor_applications'),

    # Conference Dashboard & Features
    path('conference/<int:event_pk>/', views.conference_dashboard, name='conference_dashboard'),
    path('conference/<int:event_pk>/session/<int:session_pk>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    path('events/<int:event_pk>/agendas/<int:agenda_pk>/like/', views.toggle_agenda_like, name='toggle_agenda_like'),
    path('event/<int:event_pk>/upcoming-sessions/', views.upcoming_sessions_api, name='upcoming_sessions_api'),

    # Notification API endpoints
    path('api/notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('api/notifications/archive-all/', views.archive_all_notifications, name='archive_all_notifications'),
    path('api/notifications/count/', views.notification_count, name='notification_count'),

    # Session API endpoints
    path('api/session/<int:session_pk>/speakers/', views.session_speakers_api, name='session_speakers_api'),

    # Global Speaker Management
    path('speakers/', views.speaker_list_global, name='speaker_list_global'),
    path('speakers/create/', views.speaker_create_global, name='speaker_create_global'),
    path('speakers/<int:speaker_pk>/edit/', views.speaker_edit_global, name='speaker_edit_global'),
    path('speakers/<int:speaker_pk>/delete/', views.speaker_delete_global, name='speaker_delete_global'),

    # Global Sponsor Management
    path('sponsors/', views.sponsor_list_global, name='sponsor_list_global'),
    path('sponsors/create/', views.sponsor_create_global, name='sponsor_create_global'),
    path('sponsors/<int:sponsor_pk>/edit/', views.sponsor_edit_global, name='sponsor_edit_global'),
    path('sponsors/<int:sponsor_pk>/delete/', views.sponsor_delete_global, name='sponsor_delete_global'),

    # Event-specific Sponsor Management
    path('events/<int:event_pk>/sponsors/', views.event_sponsors_manage, name='event_sponsors_manage'),
    path('api/events/<int:event_pk>/sponsors/', views.event_sponsors_api, name='event_sponsors_api'),

    # Supporting Materials Management
    path('events/<int:event_pk>/materials/create/', views.supporting_material_create, name='supporting_material_create'),
    path('events/<int:event_pk>/materials/<int:material_pk>/edit/', views.supporting_material_edit, name='supporting_material_edit'),
    path('events/<int:event_pk>/materials/<int:material_pk>/delete/', views.supporting_material_delete, name='supporting_material_delete'),
    path('api/events/<int:event_pk>/materials/', views.supporting_material_api, name='supporting_material_api'),

    # Venue Map Management
    path('events/<int:event_pk>/maps/create/', views.venue_map_create, name='venue_map_create'),
    path('events/<int:event_pk>/maps/<int:map_pk>/edit/', views.venue_map_edit, name='venue_map_edit'),
    path('events/<int:event_pk>/maps/<int:map_pk>/delete/', views.venue_map_delete, name='venue_map_delete'),

    # Announcements Management
    path('announcements/', views.announcements, name='announcements'),
    path('announcements/create/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:pk>/edit/', views.announcement_update, name='announcement_update'),
    path('announcements/<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),
]