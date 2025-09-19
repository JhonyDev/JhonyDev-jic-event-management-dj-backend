from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from allauth.account.decorators import login_required as allauth_login_required
from .forms import EventForm, LoginForm
from .models import Event
from django.shortcuts import render, redirect
from .models import Event
from .forms import EventForm





from .models import Event, Registration
from .serializers import (
    EventSerializer, EventCreateSerializer,
    RegistrationSerializer, UserSerializer
)


class EventViewSet(viewsets.ModelViewSet):
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
        events = Event.objects.filter(organizer=request.user)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def registered_events(self, request):
        events = Event.objects.filter(
            registrations__user=request.user,
            registrations__status='confirmed'
        )
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)


class RegistrationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Registration.objects.filter(user=self.request.user)

def dashboard(request):
    return render(request, "api/dashboard.html")

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("event_list")
    else:
        form = LoginForm()
    return render(request, "auth/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required(login_url='/accounts/login/')
def event_list(request):
    events = Event.objects.filter(organizer=request.user)
    return render(request, "events/event_list.html", {"events": events})

@login_required(login_url='/accounts/login/')
def event_create(request):
    if request.method == "POST" or request.method == "PUT":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            return redirect("event_list")
    else:
        form = EventForm()
    return render(request, "events/event_form.html", {"form": form})

@login_required(login_url='/accounts/login/')
def event_update(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect("event_list")
    else:
        form = EventForm(instance=event)
    return render(request, "events/event_form.html", {"form": form})

@login_required(login_url='/accounts/login/')
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    if request.method == "POST":
        event.delete()
        return redirect("event_list")
    return render(request, "events/event_confirm_delete.html", {"event": event})

def dashboard(request):
    events = Event.objects.all()
    return render(request, "dashboard.html", {"events": events})

def dashboard(request):
    events = Event.objects.all()

    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("dashboard")  # refresh after adding
    else:
        form = EventForm()

    return render(request, "dashboard.html", {"events": events, "form": form})
