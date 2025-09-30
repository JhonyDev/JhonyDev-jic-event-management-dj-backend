from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import models

from .models import Event, Registration, Agenda, Session, Speaker, VenueMap, FAQ, ContactInfo, AppContent, Announcement
from .serializers import (
    EventSerializer, EventCreateSerializer,
    RegistrationSerializer, UserSerializer,
    AgendaSerializer, SessionSerializer, SpeakerSerializer,
    AgendaSessionSerializer, FAQSerializer, ContactInfoSerializer,
    AppContentSerializer, AnnouncementSerializer
)


class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint for events management.

    Provides CRUD operations for events and registration actions.
    """
    queryset = Event.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return EventCreateSerializer
        return EventSerializer

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def register(self, request, pk=None):
        """Register the current user for an event"""
        event = self.get_object()
        user = request.user

        if Registration.objects.filter(event=event, user=user).exists():
            return Response(
                {'detail': 'Already registered for this event'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if event.registrations.filter(status='confirmed').count() >= event.max_attendees:
            return Response(
                {'detail': 'Event is full'},
                status=status.HTTP_400_BAD_REQUEST
            )

        registration = Registration.objects.create(
            event=event,
            user=user,
            status='confirmed'
        )
        serializer = RegistrationSerializer(registration)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def unregister(self, request, pk=None):
        """Unregister the current user from an event"""
        event = self.get_object()
        user = request.user

        try:
            registration = Registration.objects.get(event=event, user=user)
            registration.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Registration.DoesNotExist:
            return Response(
                {'detail': 'Not registered for this event'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_events(self, request):
        """Get all events organized by the current user"""
        events = Event.objects.filter(organizer=request.user)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def registered_events(self, request):
        """Get all events the current user is registered for"""
        events = Event.objects.filter(
            registrations__user=request.user,
            registrations__status='confirmed'
        )
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming browseable events (published and allow signup without QR)"""
        from django.utils import timezone
        events = Event.objects.filter(
            date__gte=timezone.now(),
            status='published',
            allow_signup_without_qr=True
        ).order_by('date')
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def upcoming_registered(self, request):
        """Get upcoming events the current user is registered for"""
        from django.utils import timezone
        events = Event.objects.filter(
            registrations__user=request.user,
            registrations__status='confirmed',
            date__gte=timezone.now(),
            status='published'
        ).distinct().order_by('date')
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def registration_status(self, request, pk=None):
        """Check if the current user is registered for this event"""
        event = self.get_object()
        user = request.user

        is_registered = Registration.objects.filter(
            event=event,
            user=user,
            status='confirmed'
        ).exists()

        return Response({
            'is_registered': is_registered,
            'event_id': event.id,
            'event_title': event.title
        })

    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """Handle attendee check-in from React Native app"""
        event = self.get_object()

        # Get user ID from the request (sent from React Native app)
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'User ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find the registration
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            registration = Registration.objects.get(
                event=event,
                user=user,
                status='confirmed'
            )
        except (User.DoesNotExist, Registration.DoesNotExist):
            return Response(
                {'error': 'Registration not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Store check-in in session for the organizer to retrieve
        request.session[f'pending_checkin_{event.id}'] = {
            'registration_id': registration.id,
            'name': user.get_full_name() or user.username,
            'email': user.email,
            'registered_date': registration.registered_at.strftime('%Y-%m-%d %H:%M'),
            'checked_in_at': timezone.now().isoformat()
        }

        return Response({
            'success': True,
            'message': 'Check-in successful',
            'attendee': {
                'name': user.get_full_name() or user.username,
                'email': user.email,
                'event': event.title
            }
        })

    @action(detail=True, methods=['get'])
    def pending_checkins(self, request, pk=None):
        """Get pending check-ins for the organizer's screen"""
        event = self.get_object()

        # Only allow event organizers to access this
        if event.organizer != request.user:
            return Response(
                {'error': 'Unauthorized'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check for pending check-in in session
        pending_key = f'pending_checkin_{event.id}'
        if pending_key in request.session:
            attendee = request.session.pop(pending_key)  # Remove after retrieving
            return Response({
                'pending_checkin': True,
                'attendee': attendee
            })

        return Response({'pending_checkin': False})

    @action(detail=True, methods=['get'])
    def agenda(self, request, pk=None):
        """Get agenda data for an event grouped by agendas/days"""
        event = self.get_object()

        # Get all agendas for this event with their sessions
        agendas = Agenda.objects.filter(event=event).prefetch_related(
            'sessions__speakers'
        ).order_by('order', 'date')

        # Format agendas with their sessions
        agenda_data = []
        for agenda in agendas:
            # Get sessions for this agenda
            sessions = agenda.sessions.all().order_by('order', 'start_time')

            session_list = []
            for session in sessions:
                # Get all speakers for this session
                speakers_list = []
                for speaker in session.speakers.all():
                    speakers_list.append({
                        'id': speaker.id,
                        'name': speaker.name,
                        'title': speaker.title,
                        'company': speaker.company
                    })

                # For backward compatibility, keep the single speaker field
                speaker_name = None
                if session.speakers.exists():
                    speaker_name = session.speakers.first().name

                session_data = {
                    'id': session.id,
                    'time': session.start_time.strftime('%I:%M %p') if session.start_time else 'TBD',
                    'duration': self._calculate_duration(session.start_time, session.end_time),
                    'title': session.title,
                    'description': session.description,
                    'location': session.location or 'TBD',
                    'type': session.session_type,
                    'speaker': speaker_name,  # Keep for backward compatibility
                    'speakers': speakers_list  # New field with all speakers
                }
                session_list.append(session_data)

            agenda_info = {
                'id': agenda.id,
                'title': agenda.title,
                'description': agenda.description,
                'date': agenda.date.strftime('%Y-%m-%d') if agenda.date else None,
                'day_number': agenda.day_number,
                'order': agenda.order,
                'sessions': session_list
            }
            agenda_data.append(agenda_info)

        return Response(agenda_data)

    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """Get all sessions for an event"""
        event = self.get_object()
        sessions = Session.objects.filter(agenda__event=event).prefetch_related('speakers').order_by('agenda__order', 'order', 'start_time')
        serializer = SessionSerializer(sessions, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def speakers(self, request, pk=None):
        """Get all speakers for an event"""
        event = self.get_object()
        speakers = Speaker.objects.filter(sessions__agenda__event=event).distinct().order_by('name')

        # Format speakers with their sessions and expertise
        speakers_data = []
        for speaker in speakers:
            speaker_sessions = Session.objects.filter(
                agenda__event=event,
                speakers=speaker
            ).values_list('title', flat=True)

            speaker_data = {
                'id': speaker.id,
                'name': speaker.name,
                'title': speaker.title,
                'company': speaker.company,
                'bio': speaker.bio,
                'email': speaker.email,
                'sessions': list(speaker_sessions),
                'expertise': self._get_speaker_expertise(speaker),
                'avatar': self._get_speaker_initials(speaker.name)
            }
            speakers_data.append(speaker_data)

        return Response(speakers_data)

    @action(detail=True, methods=['get'])
    def location(self, request, pk=None):
        """Get location details for an event"""
        event = self.get_object()

        # Get venue maps for this event
        venue_maps = VenueMap.objects.filter(event=event, is_active=True).order_by('order', 'title')

        venue_maps_data = []
        for venue_map in venue_maps:
            map_data = {
                'id': venue_map.id,
                'title': venue_map.title,
                'description': venue_map.description,
                'image': request.build_absolute_uri(venue_map.image.url) if venue_map.image else None,
                'order': venue_map.order
            }
            venue_maps_data.append(map_data)

        # Return location data structure that matches mobile app expectations
        location_data = {
            'venue': event.location,
            'address': event.venue_details or event.location,
            'coordinates': {
                'latitude': None,  # Will be resolved by Google Maps search
                'longitude': None  # Will be resolved by Google Maps search
            },
            'venue_maps': venue_maps_data  # Add venue maps
        }

        return Response(location_data)

    def _calculate_duration(self, start_time, end_time):
        """Helper method to calculate session duration"""
        if start_time and end_time:
            from datetime import datetime, date
            start = datetime.combine(date.today(), start_time)
            end = datetime.combine(date.today(), end_time)
            duration = end - start
            total_minutes = int(duration.total_seconds() / 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60

            if hours > 0:
                return f"{hours}h {minutes}min" if minutes > 0 else f"{hours}h"
            else:
                return f"{minutes}min"
        return '30 min'  # Default duration

    def _get_speaker_expertise(self, speaker):
        """Helper method to get speaker expertise from their sessions"""
        # You can enhance this by adding an expertise field to Speaker model
        session_types = Session.objects.filter(speakers=speaker).values_list('session_type', flat=True).distinct()

        expertise_map = {
            'keynote': 'Leadership',
            'workshop': 'Hands-on Training',
            'panel': 'Industry Expert',
            'presentation': 'Technical Specialist'
        }

        expertise = [expertise_map.get(session_type, 'Expert') for session_type in session_types]
        if not expertise:
            expertise = ['Industry Expert']

        return expertise

    def _get_speaker_initials(self, name):
        """Helper method to get speaker initials for avatar"""
        if not name:
            return 'SP'

        parts = name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[1][0]}".upper()
        elif len(parts) == 1:
            return f"{parts[0][:2]}".upper()
        return 'SP'


class RegistrationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing registrations.

    Users can only view their own registrations.
    """
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Registration.objects.filter(user=self.request.user)


class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing FAQs.

    Returns active FAQs grouped by category.
    """
    queryset = FAQ.objects.filter(is_active=True).order_by('category', 'order', 'question')
    serializer_class = FAQSerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        """Return FAQs grouped by category"""
        faqs = self.get_queryset()
        grouped_faqs = {}

        for faq in faqs:
            category = faq.category
            if category not in grouped_faqs:
                grouped_faqs[category] = []

            grouped_faqs[category].append({
                'id': faq.id,
                'question': faq.question,
                'answer': faq.answer,
                'order': faq.order
            })

        return Response(grouped_faqs)


class ContactInfoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing contact information.

    Returns active contact information ordered by type and order.
    """
    queryset = ContactInfo.objects.filter(is_active=True).order_by('contact_type', 'order')
    serializer_class = ContactInfoSerializer
    permission_classes = [AllowAny]


class AppContentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for app content like Privacy Policy, Help & Support, About.
    """
    queryset = AppContent.objects.filter(is_active=True)
    serializer_class = AppContentSerializer
    permission_classes = [AllowAny]
    lookup_field = 'content_type'

    @action(detail=False, methods=['get'])
    def privacy_policy(self, request):
        """Get privacy policy content"""
        try:
            content = AppContent.objects.get(content_type='privacy_policy', is_active=True)
            serializer = self.get_serializer(content)
            return Response(serializer.data)
        except AppContent.DoesNotExist:
            return Response({'detail': 'Privacy policy not found'}, status=404)

    @action(detail=False, methods=['get'])
    def help_support(self, request):
        """Get help & support content"""
        try:
            content = AppContent.objects.get(content_type='help_support', is_active=True)
            serializer = self.get_serializer(content)
            return Response(serializer.data)
        except AppContent.DoesNotExist:
            return Response({'detail': 'Help & support content not found'}, status=404)

    @action(detail=False, methods=['get'])
    def about(self, request):
        """Get about content"""
        try:
            content = AppContent.objects.get(content_type='about', is_active=True)
            serializer = self.get_serializer(content)
            return Response(serializer.data)
        except AppContent.DoesNotExist:
            return Response({'detail': 'About content not found'}, status=404)


class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing announcements.

    Returns active announcements visible to the current user.
    """
    queryset = Announcement.objects.filter(is_active=True)
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter announcements based on user's registered events"""
        from django.utils import timezone

        user = self.request.user
        current_time = timezone.now()

        # Get user's registered events
        user_events = Event.objects.filter(
            registrations__user=user,
            registrations__status='confirmed'
        )

        # Filter announcements that are:
        # 1. General announcements from organizers of events user is registered for
        # 2. Event-specific announcements for events user is registered for
        # 3. Not expired
        queryset = Announcement.objects.filter(
            is_active=True,
            publish_date__lte=current_time
        ).filter(
            models.Q(
                type='general',
                author__organized_events__in=user_events
            ) | models.Q(
                type='event_specific',
                event__in=user_events
            )
        ).filter(
            models.Q(expire_date__isnull=True) | models.Q(expire_date__gt=current_time)
        ).distinct().order_by('-priority', '-created_at')

        return queryset