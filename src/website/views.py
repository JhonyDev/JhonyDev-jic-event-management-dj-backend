from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from src.api.models import Event


def landing_page(request):
    """Landing page for the website"""
    upcoming_events = Event.objects.filter(date__gte=timezone.now()).order_by('date')[:6]
    total_events = Event.objects.count()

    context = {
        'upcoming_events': upcoming_events,
        'total_events': total_events,
    }
    return render(request, "website/landing.html", context)


def about(request):
    """About page"""
    return render(request, "website/about.html")


def contact(request):
    """Contact page"""
    return render(request, "website/contact.html")


def event_browse(request):
    """Browse all public events"""
    # Show published and cancelled events that haven't passed yet
    events = Event.objects.filter(
        status__in=['published', 'cancelled'],
        date__gte=timezone.now()
    ).order_by('date')

    # Get user's registrations if authenticated
    user_registrations = []
    if request.user.is_authenticated:
        from src.api.models import Registration
        user_registrations = list(Registration.objects.filter(
            user=request.user,
            status='confirmed'
        ).values_list('event_id', flat=True))

    context = {
        'events': events,
        'user_registrations': user_registrations,
    }
    return render(request, "website/events_browse.html", context)


def event_detail(request, pk):
    """Public event detail/landing page - Fixed version"""
    # Get the event - show published events to everyone, draft events only to organizers
    if request.user.is_authenticated:
        # Authenticated users can see their own draft events
        try:
            event = Event.objects.get(pk=pk, organizer=request.user)
        except Event.DoesNotExist:
            # If not their event, only show published ones
            event = get_object_or_404(Event, pk=pk, status='published')
    else:
        # Anonymous users can only see published events
        event = get_object_or_404(Event, pk=pk, status='published')

    # Get event-related data
    agendas = event.agendas.all().prefetch_related('sessions')

    # Get sessions through agendas
    from src.api.models import Session
    sessions = Session.objects.filter(agenda__event=event).select_related('agenda')

    # Get speakers through sessions
    from src.api.models import Speaker
    speakers = Speaker.objects.filter(sessions__agenda__event=event).distinct()

    sponsors = event.sponsors.all()

    context = {
        'event': event,
        'agendas': agendas,
        'sessions': sessions,
        'speakers': speakers,
        'sponsors': sponsors,
    }
    return render(request, "website/event_detail.html", context)


def event_info(request, pk):
    """Event information detail page"""
    if request.user.is_authenticated:
        try:
            event = Event.objects.get(pk=pk, organizer=request.user)
        except Event.DoesNotExist:
            event = get_object_or_404(Event, pk=pk, status='published')
    else:
        event = get_object_or_404(Event, pk=pk, status='published')

    sponsors = event.sponsors.all()

    # Calculate event duration in days
    event_days = 1  # Default for single day events
    if event.end_date and event.end_date.date() != event.date.date():
        event_days = (event.end_date.date() - event.date.date()).days + 1

    context = {
        'event': event,
        'sponsors': sponsors,
        'event_days': event_days,
    }
    return render(request, "website/event_info.html", context)


def event_agenda(request, pk):
    """Event agenda detail page"""
    if request.user.is_authenticated:
        try:
            event = Event.objects.get(pk=pk, organizer=request.user)
        except Event.DoesNotExist:
            event = get_object_or_404(Event, pk=pk, status='published')
    else:
        event = get_object_or_404(Event, pk=pk, status='published')

    agendas = event.agendas.all().prefetch_related('sessions')

    from src.api.models import Session
    sessions = Session.objects.filter(agenda__event=event).select_related('agenda')

    context = {
        'event': event,
        'agendas': agendas,
        'sessions': sessions,
    }
    return render(request, "website/event_agenda.html", context)


def event_speakers(request, pk):
    """Event speakers detail page"""
    if request.user.is_authenticated:
        try:
            event = Event.objects.get(pk=pk, organizer=request.user)
        except Event.DoesNotExist:
            event = get_object_or_404(Event, pk=pk, status='published')
    else:
        event = get_object_or_404(Event, pk=pk, status='published')

    from src.api.models import Speaker
    speakers = Speaker.objects.filter(sessions__agenda__event=event).distinct()

    context = {
        'event': event,
        'speakers': speakers,
    }
    return render(request, "website/event_speakers.html", context)


def event_maps(request, pk):
    """Event maps detail page"""
    if request.user.is_authenticated:
        try:
            event = Event.objects.get(pk=pk, organizer=request.user)
        except Event.DoesNotExist:
            event = get_object_or_404(Event, pk=pk, status='published')
    else:
        event = get_object_or_404(Event, pk=pk, status='published')

    # Get venue maps if they exist
    venue_maps = []
    try:
        from src.api.models import VenueMap
        venue_maps = VenueMap.objects.filter(event=event)
    except:
        pass

    context = {
        'event': event,
        'venue_maps': venue_maps,
    }
    return render(request, "website/event_maps.html", context)