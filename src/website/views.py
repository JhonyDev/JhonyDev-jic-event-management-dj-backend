from django.shortcuts import render
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
    events = Event.objects.filter(date__gte=timezone.now()).order_by('date')

    context = {
        'events': events,
    }
    return render(request, "website/events_browse.html", context)