from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from src.api.forms import EventForm, LoginForm
from src.api.models import Event, Registration


@login_required(login_url='/accounts/login/')
def dashboard(request):
    """Main dashboard view for authenticated users"""
    events = Event.objects.filter(organizer=request.user)
    registrations = Registration.objects.filter(user=request.user, status='confirmed')

    context = {
        'events': events,
        'registrations': registrations,
        'total_events': events.count(),
        'total_registrations': registrations.count(),
    }
    return render(request, "portal/dashboard.html", context)


@login_required(login_url='/accounts/login/')
def event_list(request):
    """List all events for the current user"""
    events = Event.objects.filter(organizer=request.user)
    return render(request, "portal/events/event_list.html", {"events": events})


@login_required(login_url='/accounts/login/')
def event_create(request):
    """Create a new event"""
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            return redirect("portal:event_list")
    else:
        form = EventForm()
    return render(request, "portal/events/event_form.html", {"form": form})


@login_required(login_url='/accounts/login/')
def event_update(request, pk):
    """Update an existing event"""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect("portal:event_list")
    else:
        form = EventForm(instance=event)
    return render(request, "portal/events/event_form.html", {"form": form})


@login_required(login_url='/accounts/login/')
def event_delete(request, pk):
    """Delete an event"""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    if request.method == "POST":
        event.delete()
        return redirect("portal:event_list")
    return render(request, "portal/events/event_confirm_delete.html", {"event": event})


@login_required(login_url='/accounts/login/')
def event_detail(request, pk):
    """View event details"""
    event = get_object_or_404(Event, pk=pk)
    is_registered = Registration.objects.filter(event=event, user=request.user).exists()
    registrations = event.registrations.filter(status='confirmed')

    context = {
        'event': event,
        'is_registered': is_registered,
        'registrations': registrations,
        'available_spots': event.max_attendees - registrations.count(),
    }
    return render(request, "portal/events/event_detail.html", context)


@login_required(login_url='/accounts/login/')
def my_registrations(request):
    """View all events user is registered for"""
    registrations = Registration.objects.filter(user=request.user).select_related('event')
    return render(request, "portal/registrations/my_registrations.html", {"registrations": registrations})


@login_required(login_url='/accounts/login/')
def register_for_event(request, pk):
    """Register for an event"""
    event = get_object_or_404(Event, pk=pk)

    if request.method == "POST":
        if not Registration.objects.filter(event=event, user=request.user).exists():
            if event.registrations.filter(status='confirmed').count() < event.max_attendees:
                Registration.objects.create(
                    event=event,
                    user=request.user,
                    status='confirmed'
                )
        return redirect("portal:event_detail", pk=pk)

    return redirect("portal:event_detail", pk=pk)


@login_required(login_url='/accounts/login/')
def unregister_from_event(request, pk):
    """Unregister from an event"""
    event = get_object_or_404(Event, pk=pk)

    if request.method == "POST":
        Registration.objects.filter(event=event, user=request.user).delete()
        return redirect("portal:event_detail", pk=pk)

    return redirect("portal:event_detail", pk=pk)