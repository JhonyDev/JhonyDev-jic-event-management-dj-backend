from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import models
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import time
import queue
import threading

from .models import Event, Registration, Agenda, Session, Speaker, VenueMap, FAQ, ContactInfo, AppContent, Announcement, SessionRegistration, QuickAction, SupportingMaterial
from .serializers import (
    EventSerializer, EventCreateSerializer,
    RegistrationSerializer, UserSerializer,
    AgendaSerializer, SessionSerializer, SpeakerSerializer,
    AgendaSessionSerializer, FAQSerializer, ContactInfoSerializer,
    AppContentSerializer, AnnouncementSerializer,
    QuickActionSerializer, SupportingMaterialSerializer
)

# Global dictionary to store SSE connections per event
event_sse_connections = {}


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

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_path='registration-types')
    def registration_types(self, request, pk=None):
        """Get registration types for this event"""
        event = self.get_object()
        from .models import EventRegistrationType

        reg_types = EventRegistrationType.objects.filter(
            event=event,
            is_active=True
        ).order_by('order', 'name')

        data = [{
            'id': rt.id,
            'name': rt.name,
            'description': rt.description,
            'is_paid': rt.is_paid,
            'amount': str(rt.amount) if rt.is_paid else '0',
            'payment_methods': rt.payment_methods,
        } for rt in reg_types]

        return Response(data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_path='workshops')
    def workshops(self, request, pk=None):
        """Get workshops/sessions for this event that allow registration"""
        event = self.get_object()

        # Get sessions that allow registration and are marked as workshops
        workshops = Session.objects.filter(
            agenda__event=event,
            allow_registration=True
        ).select_related('agenda').order_by('agenda__order', 'start_time')

        data = [{
            'id': session.id,
            'title': session.title,
            'description': session.description,
            'is_paid': session.is_paid_session,
            'fee': str(session.session_fee) if session.is_paid_session else '0',
            'start_time': session.start_time,
            'end_time': session.end_time,
            'location': session.location,
            'slots_available': session.slots_available,
            'slots_taken': SessionRegistration.objects.filter(session=session).count() if session.slots_available else None,
        } for session in workshops]

        return Response(data)

    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """Handle attendee check-in from React Native app for Entry Pass"""
        event = self.get_object()

        # Get user ID from the request (sent from React Native app)
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'User ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find the registration
        from django.utils import timezone
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

        # Check if already checked in
        from .models import CheckIn
        existing_checkin = CheckIn.objects.filter(
            registration=registration,
            event=event
        ).first()

        if existing_checkin:
            # Already checked in - still show in modal but indicate it
            attendee_data = {
                'registration_id': registration.id,
                'user_id': user.id,
                'name': user.get_full_name() or user.username,
                'email': user.email,
                'phone': getattr(user, 'phone', ''),
                'organization': getattr(user, 'organization', ''),
                'registered_date': registration.registered_at.strftime('%Y-%m-%d %H:%M'),
                'checked_in_at': existing_checkin.checked_in_at.isoformat(),
                'profile_image': user.profile_image.url if hasattr(user, 'profile_image') and user.profile_image else None,
                'already_checked_in': True
            }
        else:
            # Create new check-in record
            checkin = CheckIn.objects.create(
                event=event,
                user=user,
                registration=registration,
                checked_in_by=request.user if request.user.is_authenticated else None,
                check_in_method='qr_code'
            )

            attendee_data = {
                'registration_id': registration.id,
                'user_id': user.id,
                'name': user.get_full_name() or user.username,
                'email': user.email,
                'phone': getattr(user, 'phone', ''),
                'organization': getattr(user, 'organization', ''),
                'registered_date': registration.registered_at.strftime('%Y-%m-%d %H:%M'),
                'checked_in_at': checkin.checked_in_at.isoformat(),
                'profile_image': user.profile_image.url if hasattr(user, 'profile_image') and user.profile_image else None,
                'already_checked_in': False
            }

        # Store in Django cache for polling (Entry Pass system)
        from django.core.cache import cache
        cache_key = f'pending_checkin_{event.id}'
        # Store for 60 seconds (will be picked up by polling)
        cache.set(cache_key, attendee_data, 60)

        # Also send to SSE clients if connected
        event_id = str(event.id)
        if event_id in event_sse_connections:
            message = json.dumps({
                'type': 'attendee_scanned',
                'data': attendee_data
            })

            # Send to all connected clients for this event
            for client_queue in event_sse_connections[event_id]:
                try:
                    client_queue.put(f"data: {message}\n\n")
                except:
                    pass

        return Response({
            'success': True,
            'message': 'Check-in successful. Entry pass will be generated.',
            'attendee': {
                'name': user.get_full_name() or user.username,
                'email': user.email,
                'event': event.title
            }
        })

    @action(detail=True, methods=['get'])
    @method_decorator(csrf_exempt)
    def sse_stream(self, request, pk=None):
        """Server-Sent Events endpoint for real-time updates"""
        from django.http import HttpResponseForbidden
        import logging

        logger = logging.getLogger(__name__)

        event = self.get_object()

        # Debug logging
        logger.info(f"SSE request from user: {request.user}")
        logger.info(f"User authenticated: {request.user.is_authenticated}")
        logger.info(f"Event organizer: {event.organizer}")

        # Check if user is authenticated
        if not request.user.is_authenticated:
            logger.warning("SSE connection rejected - user not authenticated")
            return HttpResponseForbidden('Authentication required')

        # Only allow event organizers to access this
        if event.organizer != request.user:
            logger.warning(f"SSE connection rejected - user {request.user} is not organizer of event {event.id}")
            return HttpResponseForbidden('Only event organizers can access this endpoint')

        def event_stream():
            event_id = str(event.id)
            client_queue = queue.Queue()

            # Add this client to the connections
            if event_id not in event_sse_connections:
                event_sse_connections[event_id] = []
            event_sse_connections[event_id].append(client_queue)

            # Send initial connection message
            yield "data: {\"type\": \"connected\", \"message\": \"SSE connection established\"}\n\n"

            try:
                while True:
                    try:
                        # Wait for messages with timeout to send heartbeat
                        message = client_queue.get(timeout=30)
                        yield message
                    except queue.Empty:
                        # Send heartbeat to keep connection alive
                        yield ": heartbeat\n\n"
            finally:
                # Remove client on disconnect
                if event_id in event_sse_connections:
                    if client_queue in event_sse_connections[event_id]:
                        event_sse_connections[event_id].remove(client_queue)
                    if not event_sse_connections[event_id]:
                        del event_sse_connections[event_id]

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    @action(detail=True, methods=['get'])
    def recent_checkins(self, request, pk=None):
        """Get recent check-ins for an event"""
        event = self.get_object()

        # Check if user is organizer
        if event.organizer != request.user:
            return Response(
                {'error': 'Only organizers can view check-ins'},
                status=status.HTTP_403_FORBIDDEN
            )

        from .models import CheckIn
        # Get last 20 check-ins
        recent_checkins = CheckIn.objects.filter(event=event).select_related('user', 'registration')[:20]

        checkins_data = []
        for checkin in recent_checkins:
            checkins_data.append({
                'user_id': checkin.user.id,
                'registration_id': checkin.registration.id,
                'name': checkin.user.get_full_name() or checkin.user.username,
                'email': checkin.user.email,
                'phone': getattr(checkin.user, 'phone', ''),
                'organization': getattr(checkin.user, 'organization', ''),
                'registered_date': checkin.registration.registered_at.strftime('%Y-%m-%d %H:%M'),
                'checked_in_at': checkin.checked_in_at.isoformat(),
                'profile_image': checkin.user.profile_image.url if hasattr(checkin.user, 'profile_image') and checkin.user.profile_image else None
            })

        # Also get total stats
        total_registered = Registration.objects.filter(event=event, status='confirmed').count()
        total_checked_in = CheckIn.objects.filter(event=event).count()

        return Response({
            'recent_checkins': checkins_data,
            'stats': {
                'total_registered': total_registered,
                'total_checked_in': total_checked_in,
                'percentage': round((total_checked_in / total_registered * 100) if total_registered > 0 else 0, 1)
            }
        })

    @action(detail=True, methods=['get'])
    def pending_checkins(self, request, pk=None):
        """Get pending check-ins for the organizer's screen"""
        from django.core.cache import cache

        event = self.get_object()

        # Only allow event organizers to access this
        if event.organizer != request.user:
            return Response(
                {'error': 'Unauthorized'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check for pending check-in in cache (instead of session)
        cache_key = f'pending_checkin_{event.id}'
        attendee = cache.get(cache_key)

        if attendee:
            # Remove after retrieving
            cache.delete(cache_key)
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

                # Check registration info for the session
                slots_taken = SessionRegistration.objects.filter(session=session).count()
                is_registered = False
                if request.user.is_authenticated:
                    is_registered = SessionRegistration.objects.filter(
                        session=session,
                        user=request.user
                    ).exists()

                # Check if session has attachments
                has_attachments = session.supporting_materials.filter(is_public=True).exists()
                attachment_count = session.supporting_materials.filter(is_public=True).count()

                session_data = {
                    'id': session.id,
                    'time': session.start_time.strftime('%I:%M %p') if session.start_time else 'TBD',
                    'duration': self._calculate_duration(session.start_time, session.end_time),
                    'title': session.title,
                    'description': session.description,
                    'location': session.location or 'TBD',
                    'type': session.session_type,
                    'speaker': speaker_name,  # Keep for backward compatibility
                    'speakers': speakers_list,  # New field with all speakers
                    # Session registration fields
                    'allow_registration': session.allow_registration,
                    'slots_available': session.slots_available,
                    'slots_taken': slots_taken,
                    'is_registered': is_registered,
                    # Payment fields
                    'is_paid_session': session.is_paid_session,
                    'session_fee': str(session.session_fee) if session.session_fee else '0',
                    'payment_methods': session.payment_methods or [],
                    # Attachment fields
                    'has_attachments': has_attachments,
                    'attachment_count': attachment_count
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


class SessionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for session management with registration
    """
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Session.objects.all()

    @action(detail=True, methods=['post'])
    def register(self, request, pk=None):
        """Register current user for a session"""
        session = self.get_object()

        # Check if registration is allowed
        if not session.allow_registration:
            return Response(
                {'error': 'Registration is not allowed for this session'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if already registered
        if SessionRegistration.objects.filter(session=session, user=request.user).exists():
            return Response(
                {'message': 'You are already registered for this session'},
                status=status.HTTP_200_OK
            )

        # Check slot availability
        if session.slots_available is not None:
            current_registrations = SessionRegistration.objects.filter(session=session).count()
            if current_registrations >= session.slots_available:
                return Response(
                    {'error': 'No slots available for this session'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Check if session requires payment
        if session.is_paid_session:
            from src.payments.models import JazzCashTransaction

            # Check if user has a completed payment for this session
            has_paid = JazzCashTransaction.objects.filter(
                session=session,
                user=request.user,
                status='completed'
            ).exists()

            if not has_paid:
                return Response(
                    {'error': 'Payment required for this session. Please complete payment before registering.'},
                    status=status.HTTP_402_PAYMENT_REQUIRED
                )

        # Create registration
        try:
            registration = SessionRegistration.objects.create(
                session=session,
                user=request.user
            )
            return Response({
                'message': 'Successfully registered for session',
                'registration_id': registration.id
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def unregister(self, request, pk=None):
        """Unregister current user from a session"""
        session = self.get_object()

        # Check if registered
        registration = SessionRegistration.objects.filter(
            session=session,
            user=request.user
        ).first()

        if not registration:
            return Response(
                {'error': 'You are not registered for this session'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete registration
        registration.delete()
        return Response({
            'message': 'Successfully unregistered from session'
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def attachments(self, request, pk=None):
        """Get supporting materials attached to a session"""
        session = self.get_object()

        # Get supporting materials linked to this session
        materials = session.supporting_materials.filter(
            is_public=True  # Only show public materials
        ).order_by('order', 'title')

        # Serialize the materials
        data = []
        for material in materials:
            # Get file extension
            file_extension = ''
            if material.file:
                file_name = material.file.name
                if '.' in file_name:
                    file_extension = file_name.split('.')[-1].lower()

            data.append({
                'id': material.id,
                'title': material.title,
                'description': material.description,
                'material_type': material.material_type,
                'file_extension': file_extension,
                'file': material.file.url if material.file else None,
                'file_url': request.build_absolute_uri(material.file.url) if material.file else None,
                'is_public': material.is_public,
                'order': material.order,
                'uploaded_at': material.uploaded_at.isoformat() if hasattr(material, 'uploaded_at') else None,
            })

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def registrations(self, request, pk=None):
        """Get all registrations for a session (organizers only)"""
        session = self.get_object()

        # Check if user is the event organizer
        if session.get_event() and session.get_event().organizer != request.user:
            return Response(
                {'error': 'Only event organizers can view registrations'},
                status=status.HTTP_403_FORBIDDEN
            )

        registrations = SessionRegistration.objects.filter(session=session).select_related('user')
        registration_data = []
        for reg in registrations:
            registration_data.append({
                'id': reg.id,
                'user_id': reg.user.id,
                'name': reg.user.get_full_name() or reg.user.username,
                'email': reg.user.email,
                'registered_at': reg.registered_at.isoformat()
            })

        return Response({
            'session': session.title,
            'total_registrations': len(registration_data),
            'slots_available': session.slots_available,
            'registrations': registration_data
        })


class QuickActionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Quick Actions.

    Full CRUD operations for quick actions for events.
    """
    serializer_class = QuickActionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter quick actions by event if event_id is provided"""
        queryset = QuickAction.objects.filter(is_active=True)
        event_id = self.request.query_params.get('event_id', None)

        if event_id:
            queryset = queryset.filter(event_id=event_id)

        return queryset.prefetch_related('supporting_materials').order_by('order')

    @action(detail=False, methods=['get'])
    def by_event(self, request):
        """Get all quick actions for a specific event"""
        event_id = request.query_params.get('event_id')

        if not event_id:
            return Response(
                {'error': 'event_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response(
                {'error': 'Event not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        quick_actions = QuickAction.objects.filter(
            event=event,
            is_active=True
        ).prefetch_related('supporting_materials').order_by('order')

        serializer = self.get_serializer(quick_actions, many=True)

        return Response({
            'event_id': event.id,
            'event_title': event.title,
            'quick_actions': serializer.data
        })

    @action(detail=True, methods=['get'])
    def attachments(self, request, pk=None):
        """Get supporting materials for a specific quick action"""
        try:
            quick_action = self.get_object()
            materials = quick_action.supporting_materials.filter(is_public=True)
            serializer = SupportingMaterialSerializer(materials, many=True, context={'request': request})
            return Response(serializer.data)
        except QuickAction.DoesNotExist:
            return Response(
                {'error': 'Quick action not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class SupportingMaterialViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Supporting Materials.

    Lists and retrieves supporting materials for events.
    """
    serializer_class = SupportingMaterialSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Filter materials by event and public status"""
        queryset = SupportingMaterial.objects.filter(is_public=True)
        event_id = self.request.query_params.get('event_id', None)

        if event_id:
            queryset = queryset.filter(event_id=event_id)

        return queryset.order_by('created_at')


@method_decorator(csrf_exempt, name='dispatch')
class EventRegistrationView(viewsets.ViewSet):
    """
    API endpoint for event registration from React Native app

    POST /api/event-registration/
    """
    permission_classes = [IsAuthenticated]

    def create(self, request):
        """Create event registration (without payment)"""
        try:
            print("\n" + "="*80)
            print("🔷 EVENT REGISTRATION REQUEST RECEIVED")
            print("="*80)
            print(f"User: {request.user.username} (ID: {request.user.id})")
            print(f"Request Data: {request.data}")
            print("="*80 + "\n")

            # Get event
            event_id = request.data.get('event_id')
            if not event_id:
                return Response({
                    'error': 'Event ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                event = Event.objects.get(id=event_id)
            except Event.DoesNotExist:
                return Response({
                    'error': 'Event not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Check if already registered
            existing_registration = Registration.objects.filter(
                event=event,
                user=request.user
            ).first()

            if existing_registration:
                # Return existing registration
                return Response({
                    'success': True,
                    'registration_id': existing_registration.id,
                    'message': 'Already registered for this event',
                    'status': existing_registration.status
                }, status=status.HTTP_200_OK)

            # Get registration type if provided
            registration_type = None
            registration_type_id = request.data.get('registration_type_id')
            if registration_type_id:
                try:
                    from .models import EventRegistrationType
                    registration_type = EventRegistrationType.objects.get(
                        id=registration_type_id,
                        event=event
                    )
                except EventRegistrationType.DoesNotExist:
                    return Response({
                        'error': 'Invalid registration type'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Create registration (pending until payment)
            registration = Registration.objects.create(
                event=event,
                user=request.user,
                status='pending',  # Will be confirmed after payment
                payment_status='pending',
                registration_type=registration_type,
                designation=request.data.get('designation', ''),
                affiliations=request.data.get('affiliations', ''),
                address=request.data.get('address', ''),
                country=request.data.get('country', ''),
                phone_number=request.data.get('phone_number', ''),
            )

            # Handle workshop selection (single workshop)
            selected_workshop = request.data.get('selected_workshop')
            if selected_workshop:
                try:
                    workshop = Session.objects.get(
                        id=selected_workshop,
                        agenda__event=event,
                        session_type='workshop'
                    )
                    registration.selected_workshops.add(workshop)
                except Session.DoesNotExist:
                    pass  # Ignore invalid workshop

            print(f"✅ Registration created: ID {registration.id}")

            return Response({
                'success': True,
                'registration_id': registration.id,
                'message': 'Registration created successfully',
                'status': 'pending'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"\n❌ EXCEPTION OCCURRED!")
            print(f"Exception type: {type(e).__name__}")
            print(f"Exception message: {str(e)}")
            import traceback
            print(f"Traceback:")
            print(traceback.format_exc())

            return Response({
                'error': f'Registration failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)