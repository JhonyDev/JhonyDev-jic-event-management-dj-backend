from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Event, Registration
from .serializers import (
    EventSerializer, EventCreateSerializer,
    RegistrationSerializer, UserSerializer
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
        """Get upcoming events"""
        from django.utils import timezone
        events = Event.objects.filter(date__gte=timezone.now()).order_by('date')[:10]
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)


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