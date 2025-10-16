from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
import json
from src.api.forms import (
    EventForm, AgendaForm, AgendaTopicForm, AgendaCoordinatorForm, SpeakerForm, SessionForm,
    ExhibitorForm, ExhibitionAreaForm, SelfRegistrationForm, VenueMapForm, SponsorForm, SupportingMaterialForm
)
from src.api.models import (
    Event, Agenda, AgendaTopic, AgendaCoordinator, Registration, Speaker, Session,
    Exhibitor, ExhibitionArea, VenueMap, Sponsor, SupportingMaterial,
    SessionBookmark, AgendaLike, Notification
)


@login_required(login_url="/accounts/login/")
def dashboard(request):
    """Main dashboard view for authenticated users"""
    from django.db.models import Count, Sum, Q
    from datetime import datetime, timedelta

    # Get events organized by user
    events = Event.objects.filter(organizer=request.user)
    registrations = Registration.objects.filter(user=request.user, status="confirmed")

    # Calculate comprehensive statistics
    total_events = events.count()
    published_events = events.filter(status='published').count()
    draft_events = events.filter(status='draft').count()

    # Get total attendees across all events
    total_attendees = Registration.objects.filter(
        event__organizer=request.user,
        status='confirmed'
    ).count()

    # Get total sessions and speakers
    total_sessions = Session.objects.filter(agenda__event__organizer=request.user).count()
    total_speakers = Speaker.objects.filter(sessions__agenda__event__organizer=request.user).distinct().count()

    # Set default values for removed ticket system
    total_tickets_sold = 0
    total_revenue = 0

    # Get upcoming events (next 30 days)
    upcoming_events = events.filter(
        date__gte=timezone.now(),
        date__lte=timezone.now() + timedelta(days=30)
    ).count()

    # Get recent events (last 30 days)
    recent_events = events.filter(
        date__gte=timezone.now() - timedelta(days=30),
        date__lte=timezone.now()
    ).count()

    # Get event status breakdown
    event_status_stats = events.values('status').annotate(count=Count('id'))

    # Get monthly registration trend (last 6 months)
    monthly_registrations = []
    for i in range(6):
        month_start = (timezone.now().replace(day=1) - timedelta(days=30*i))
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_count = Registration.objects.filter(
            event__organizer=request.user,
            registered_at__gte=month_start,
            registered_at__lt=month_end,
            status='confirmed'
        ).count()
        monthly_registrations.append({
            'month': month_start.strftime('%B'),
            'count': month_count
        })

    # Get recent activities (last 10)
    recent_registrations = Registration.objects.filter(
        event__organizer=request.user
    ).select_related('user', 'event').order_by('-registered_at')[:10]

    context = {
        "events": events.order_by('-date')[:10],
        "registrations": registrations,
        "total_events": total_events,
        "total_registrations": registrations.count(),
        "published_events": published_events,
        "draft_events": draft_events,
        "total_attendees": total_attendees,
        "total_sessions": total_sessions,
        "total_speakers": total_speakers,
        "total_tickets_sold": total_tickets_sold,
        "total_revenue": total_revenue,
        "upcoming_events": upcoming_events,
        "recent_events": recent_events,
        "event_status_stats": event_status_stats,
        "monthly_registrations": monthly_registrations,
        "recent_registrations": recent_registrations,
    }
    return render(request, "portal/dashboard.html", context)


@login_required(login_url="/accounts/login/")
def event_list(request):
    """List all events for the current user"""
    events = Event.objects.filter(organizer=request.user)
    return render(request, "portal/events/event_list.html", {"events": events})


@login_required(login_url="/accounts/login/")
def all_agendas(request):
    """List all agendas across all user's events"""
    agendas = Agenda.objects.filter(event__organizer=request.user).order_by('-event__date', 'order', 'date')

    context = {
        'agendas': agendas,
    }
    return render(request, "portal/events/all_agendas.html", context)


@login_required(login_url="/accounts/login/")
def all_sessions(request):
    """List all sessions across all user's events"""
    sessions = Session.objects.filter(agenda__event__organizer=request.user).order_by('-agenda__event__date', 'start_time')

    context = {
        'sessions': sessions,
    }
    return render(request, "portal/events/all_sessions.html", context)


@login_required(login_url="/accounts/login/")
def all_speakers(request):
    """List all speakers across all user's events"""
    speakers = Speaker.objects.filter(sessions__agenda__event__organizer=request.user).distinct().order_by('name')

    context = {
        'speakers': speakers,
    }
    return render(request, "portal/events/all_speakers.html", context)


@login_required(login_url="/accounts/login/")
def all_exhibitions(request):
    """List all exhibition areas across all user's events"""
    exhibition_areas = ExhibitionArea.objects.filter(event__organizer=request.user).order_by('-event__date', 'name')

    context = {
        'exhibition_areas': exhibition_areas,
    }
    return render(request, "portal/events/all_exhibitions.html", context)


@login_required(login_url="/accounts/login/")
def event_create(request):
    """Create a new event"""
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user

            # Handle is_paid_event checkbox explicitly
            event.is_paid_event = request.POST.get('is_paid_event') == 'true'

            # Handle payment_methods (checkboxes return a list)
            payment_methods = request.POST.getlist('payment_methods')
            event.payment_methods = payment_methods if payment_methods else []

            event.save()
            return redirect("portal:event_list")
    else:
        form = EventForm()
    return render(request, "portal/events/event_form.html", {"form": form})


@login_required(login_url="/accounts/login/")
def event_update(request, pk):
    """Update an existing event"""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            event = form.save(commit=False)

            # Handle is_paid_event checkbox explicitly
            event.is_paid_event = request.POST.get('is_paid_event') == 'true'

            # Handle payment_methods (checkboxes return a list)
            payment_methods = request.POST.getlist('payment_methods')
            event.payment_methods = payment_methods if payment_methods else []

            event.save()
            return redirect("portal:event_list")
    else:
        form = EventForm(instance=event)
    return render(request, "portal/events/event_form.html", {"form": form})


@login_required(login_url="/accounts/login/")
def event_delete(request, pk):
    """Delete an event"""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    if request.method == "POST":
        event.delete()
        return redirect("portal:event_list")
    return render(request, "portal/events/event_confirm_delete.html", {"event": event})


@login_required(login_url="/accounts/login/")
def event_detail(request, pk):
    """View event details with all related information"""
    from src.api.models import EventRegistrationType

    event = get_object_or_404(Event, pk=pk)
    is_registered = Registration.objects.filter(event=event, user=request.user).exists()
    registrations = event.registrations.filter(status="confirmed")

    # Get user's registration for entry pass
    user_registration = None
    if is_registered:
        user_registration = Registration.objects.filter(event=event, user=request.user, status="confirmed").first()

    # Get all related data for tabs
    sessions = Session.objects.filter(agenda__event=event).order_by('start_time')
    speakers = Speaker.objects.filter(sessions__agenda__event=event).distinct()
    exhibition_areas = event.exhibition_areas.all()
    exhibitors = event.exhibitors.filter(approved=True)
    agendas = Agenda.objects.filter(event=event).prefetch_related(
        'sessions__speakers',
        'sessions__registrations'
    ).order_by('date')

    # Get registration types for this event
    registration_types = EventRegistrationType.objects.filter(event=event).order_by('order', 'name')

    # Get registration logs if user is organizer (paginated)
    registration_logs = None
    logs_page_obj = None
    if event.organizer == request.user:
        from src.api.models import RegistrationLog
        from django.core.paginator import Paginator

        logs = RegistrationLog.objects.filter(event=event).select_related(
            'user', 'registration', 'registration_type'
        ).order_by('-timestamp')

        # Pagination - 50 logs per page
        paginator = Paginator(logs, 50)
        page_number = request.GET.get('logs_page', 1)
        logs_page_obj = paginator.get_page(page_number)

    context = {
        "event": event,
        "is_registered": is_registered,
        "user_registration": user_registration,
        "registrations": registrations,
        "available_spots": event.max_attendees - registrations.count(),
        "sessions": sessions,
        "speakers": speakers,
        "exhibition_areas": exhibition_areas,
        "exhibitors": exhibitors,
        "is_organizer": event.organizer == request.user,
        "agendas": agendas,
        "registration_types": registration_types,
        "registration_logs": logs_page_obj,
    }
    return render(request, "portal/events/event_detail.html", context)


@login_required(login_url="/accounts/login/")
def attendees(request):
    """View all attendees from events I've organized"""
    # Get all events organized by the current user
    user_events = Event.objects.filter(organizer=request.user)

    # Start with all registrations for user's events
    attendees = Registration.objects.filter(
        event__in=user_events,
        status='confirmed'
    ).select_related('user', 'event')

    # Apply event filter
    event_filter = request.GET.get('event')
    if event_filter:
        attendees = attendees.filter(event_id=event_filter)

    # Apply search filter (name or email)
    search_query = request.GET.get('search')
    if search_query:
        from django.db.models import Q
        attendees = attendees.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    # Apply sorting
    sort_by = request.GET.get('sort', 'name')
    if sort_by == 'name':
        attendees = attendees.order_by('user__first_name', 'user__last_name')
    elif sort_by == 'event':
        attendees = attendees.order_by('event__title', 'user__first_name')
    elif sort_by == 'email':
        attendees = attendees.order_by('user__email')
    else:
        attendees = attendees.order_by('user__first_name', 'user__last_name')

    return render(
        request,
        "portal/attendees/attendees.html",
        {
            "attendees": attendees,
            "user_events": user_events,
        },
    )


@login_required(login_url="/accounts/login/")
def register_for_event(request, pk):
    """Register for an event"""
    event = get_object_or_404(Event, pk=pk)

    if request.method == "POST":
        if not Registration.objects.filter(event=event, user=request.user).exists():
            if (
                event.registrations.filter(status="confirmed").count()
                < event.max_attendees
            ):
                Registration.objects.create(
                    event=event, user=request.user, status="confirmed"
                )
        return redirect("portal:event_detail", pk=pk)

    return redirect("portal:event_detail", pk=pk)


@login_required(login_url="/accounts/login/")
def unregister_from_event(request, pk):
    """Unregister from an event"""
    event = get_object_or_404(Event, pk=pk)

    if request.method == "POST":
        Registration.objects.filter(event=event, user=request.user).delete()
        return redirect("portal:event_detail", pk=pk)

    return redirect("portal:event_detail", pk=pk)


# SPEAKER MANAGEMENT
@login_required(login_url="/accounts/login/")
def speaker_list(request, event_pk):
    """List all speakers for an event"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    sessions = Session.objects.filter(agenda__event=event)
    speakers = Speaker.objects.filter(sessions__agenda__event=event).distinct()

    context = {
        'event': event,
        'speakers': speakers,
        'sessions': sessions,
    }
    return render(request, "portal/speakers/speaker_list.html", context)


@login_required(login_url="/accounts/login/")
def speaker_manage(request, event_pk, speaker_pk=None):
    """Create or update a speaker for an event"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    speaker = None

    if speaker_pk:
        speaker = get_object_or_404(Speaker, pk=speaker_pk)

    if request.method == "POST":
        form = SpeakerForm(request.POST, request.FILES, instance=speaker)
        if form.is_valid():
            speaker = form.save()
            if speaker_pk:
                messages.success(request, f"Speaker {speaker.name} updated successfully!")
            else:
                messages.success(request, f"Speaker {speaker.name} added successfully!")

            # Check for next parameter to redirect back to specific page/tab
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('portal:speaker_list', event_pk=event.pk)
    else:
        form = SpeakerForm(instance=speaker)

    context = {
        'event': event,
        'speaker': speaker,
        'form': form,
    }
    return render(request, "portal/speakers/speaker_form.html", context)


@login_required(login_url="/accounts/login/")
def speaker_delete(request, event_pk, speaker_pk):
    """Delete a speaker"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    speaker = get_object_or_404(Speaker, pk=speaker_pk)

    if request.method == "POST":
        speaker_name = speaker.name
        speaker.delete()
        messages.success(request, f"Speaker {speaker_name} deleted successfully!")
        return redirect('portal:speaker_list', event_pk=event.pk)

    context = {
        'event': event,
        'speaker': speaker,
    }
    return render(request, "portal/speakers/speaker_confirm_delete.html", context)


# AGENDA MANAGEMENT
@login_required(login_url="/accounts/login/")
def agenda_list(request, event_pk):
    """List all agendas for an event"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agendas = event.agendas.all().order_by('order', 'date')

    # Get liked agendas for the current user
    liked_agenda_ids = AgendaLike.objects.filter(
        user=request.user,
        agenda__in=agendas
    ).values_list('agenda_id', flat=True)

    context = {
        'event': event,
        'agendas': agendas,
        'liked_agenda_ids': list(liked_agenda_ids),
    }
    return render(request, "portal/agendas/agenda_list.html", context)


@login_required(login_url="/accounts/login/")
def agenda_manage(request, event_pk, agenda_pk=None):
    """Create or update an agenda"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = None

    if agenda_pk:
        agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)

    if request.method == "POST":
        form = AgendaForm(request.POST, instance=agenda, event=event)
        if form.is_valid():
            agenda = form.save(commit=False)
            agenda.event = event
            agenda.save()

            if agenda_pk:
                messages.success(request, f"Agenda '{agenda.title}' updated successfully!")
            else:
                messages.success(request, f"Agenda '{agenda.title}' created successfully!")

            # Check for next parameter to redirect back to specific page/tab
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('portal:agenda_list', event_pk=event.pk)
    else:
        form = AgendaForm(instance=agenda, event=event)

    context = {
        'event': event,
        'agenda': agenda,
        'form': form,
    }
    return render(request, "portal/agendas/agenda_form.html", context)


@login_required(login_url="/accounts/login/")
def agenda_delete(request, event_pk, agenda_pk):
    """Delete an agenda"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)

    if request.method == "POST":
        agenda_title = agenda.title
        agenda.delete()
        messages.success(request, f"Agenda '{agenda_title}' deleted successfully!")
        return redirect('portal:agenda_list', event_pk=event.pk)

    context = {
        'event': event,
        'agenda': agenda,
    }
    return render(request, "portal/agendas/agenda_confirm_delete.html", context)


@login_required(login_url="/accounts/login/")
def agenda_move_up(request, event_pk, agenda_pk):
    """Move agenda up in order"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)

    # Find the agenda with the next lower order number
    previous_agenda = Agenda.objects.filter(
        event=event,
        order__lt=agenda.order
    ).order_by('-order').first()

    if previous_agenda:
        # Swap order numbers
        agenda_order = agenda.order
        previous_order = previous_agenda.order

        agenda.order = previous_order
        previous_agenda.order = agenda_order

        agenda.save()
        previous_agenda.save()

        messages.success(request, f"Agenda '{agenda.title}' moved up!")

    # Handle redirect
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('portal:agenda_list', event_pk=event.pk)


@login_required(login_url="/accounts/login/")
def agenda_move_down(request, event_pk, agenda_pk):
    """Move agenda down in order"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)

    # Find the agenda with the next higher order number
    next_agenda = Agenda.objects.filter(
        event=event,
        order__gt=agenda.order
    ).order_by('order').first()

    if next_agenda:
        # Swap order numbers
        agenda_order = agenda.order
        next_order = next_agenda.order

        agenda.order = next_order
        next_agenda.order = agenda_order

        agenda.save()
        next_agenda.save()

        messages.success(request, f"Agenda '{agenda.title}' moved down!")

    # Handle redirect
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('portal:agenda_list', event_pk=event.pk)


@login_required(login_url="/accounts/login/")
def agenda_move_ajax(request, event_pk):
    """AJAX endpoint for moving agendas"""
    if request.method == "POST":
        event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
        agenda_pk = request.POST.get('agenda_pk')
        direction = request.POST.get('direction')

        agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)

        if direction == 'up':
            # Find the agenda with the next lower order number
            previous_agenda = Agenda.objects.filter(
                event=event,
                order__lt=agenda.order
            ).order_by('-order').first()

            if previous_agenda:
                # Swap order numbers
                agenda_order = agenda.order
                previous_order = previous_agenda.order

                agenda.order = previous_order
                previous_agenda.order = agenda_order

                agenda.save()
                previous_agenda.save()

                return JsonResponse({'success': True, 'message': f"Agenda '{agenda.title}' moved up!"})

        elif direction == 'down':
            # Find the agenda with the next higher order number
            next_agenda = Agenda.objects.filter(
                event=event,
                order__gt=agenda.order
            ).order_by('order').first()

            if next_agenda:
                # Swap order numbers
                agenda_order = agenda.order
                next_order = next_agenda.order

                agenda.order = next_order
                next_agenda.order = agenda_order

                agenda.save()
                next_agenda.save()

                return JsonResponse({'success': True, 'message': f"Agenda '{agenda.title}' moved down!"})

        return JsonResponse({'success': False, 'message': 'Unable to move agenda in that direction.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required(login_url="/accounts/login/")
def agenda_partial(request, event_pk):
    """Return partial HTML for agendas"""
    event = get_object_or_404(Event, pk=event_pk)

    # Check if user is organizer
    is_organizer = event.organizer == request.user

    context = {
        'event': event,
        'is_organizer': is_organizer,
    }
    return render(request, "portal/events/agenda_partial.html", context)


# AGENDA TOPIC MANAGEMENT
@login_required(login_url="/accounts/login/")
def agenda_topic_manage(request, event_pk, agenda_pk, topic_pk=None):
    """Create or edit agenda topic"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)

    if topic_pk:
        topic = get_object_or_404(AgendaTopic, pk=topic_pk, agenda=agenda)
        title = "Edit Topic"
    else:
        topic = None
        title = "Add Topic"

    if request.method == "POST":
        form = AgendaTopicForm(request.POST, instance=topic)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.agenda = agenda
            topic.save()

            action = "updated" if topic_pk else "created"
            messages.success(request, f"Topic '{topic.name}' {action} successfully!")
            return redirect('portal:agenda_list', event_pk=event.pk)
    else:
        form = AgendaTopicForm(instance=topic)

    context = {
        'form': form,
        'event': event,
        'agenda': agenda,
        'topic': topic,
        'title': title,
    }
    return render(request, "portal/agendas/topic_form.html", context)


@login_required(login_url="/accounts/login/")
def agenda_topic_delete(request, event_pk, agenda_pk, topic_pk):
    """Delete agenda topic"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)
    topic = get_object_or_404(AgendaTopic, pk=topic_pk, agenda=agenda)

    if request.method == "POST":
        topic_name = topic.name
        topic.delete()
        messages.success(request, f"Topic '{topic_name}' deleted successfully!")
        return redirect('portal:agenda_list', event_pk=event.pk)

    context = {
        'event': event,
        'agenda': agenda,
        'topic': topic,
    }
    return render(request, "portal/agendas/topic_confirm_delete.html", context)


# AGENDA COORDINATOR MANAGEMENT
@login_required(login_url="/accounts/login/")
def agenda_coordinator_manage(request, event_pk, agenda_pk, coordinator_pk=None):
    """Create or edit agenda coordinator"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)

    if coordinator_pk:
        coordinator = get_object_or_404(AgendaCoordinator, pk=coordinator_pk, agenda=agenda)
        title = "Edit Coordinator"
    else:
        coordinator = None
        title = "Add Coordinator"

    if request.method == "POST":
        form = AgendaCoordinatorForm(request.POST, instance=coordinator)
        if form.is_valid():
            coordinator = form.save(commit=False)
            coordinator.agenda = agenda
            coordinator.save()

            action = "updated" if coordinator_pk else "added"
            messages.success(request, f"Coordinator '{coordinator.name}' {action} successfully!")
            return redirect('portal:agenda_list', event_pk=event.pk)
    else:
        form = AgendaCoordinatorForm(instance=coordinator)

    context = {
        'form': form,
        'event': event,
        'agenda': agenda,
        'coordinator': coordinator,
        'title': title,
    }
    return render(request, "portal/agendas/coordinator_form.html", context)


@login_required(login_url="/accounts/login/")
def agenda_coordinator_delete(request, event_pk, agenda_pk, coordinator_pk):
    """Delete agenda coordinator"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)
    coordinator = get_object_or_404(AgendaCoordinator, pk=coordinator_pk, agenda=agenda)

    if request.method == "POST":
        coordinator_name = coordinator.name
        coordinator.delete()
        messages.success(request, f"Coordinator '{coordinator_name}' removed successfully!")
        return redirect('portal:agenda_list', event_pk=event.pk)

    context = {
        'event': event,
        'agenda': agenda,
        'coordinator': coordinator,
    }
    return render(request, "portal/agendas/coordinator_confirm_delete.html", context)


# SESSION/AGENDA MANAGEMENT
@login_required(login_url="/accounts/login/")
def session_list(request, event_pk, agenda_pk=None):
    """List all sessions for an event or specific agenda"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = None

    if agenda_pk:
        agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)
        sessions = agenda.sessions.all().order_by('start_time')
    else:
        # Show all sessions across all agendas
        sessions = Session.objects.filter(agenda__event=event).order_by('agenda__order', 'start_time')

    context = {
        'event': event,
        'agenda': agenda,
        'sessions': sessions,
        'agendas': event.agendas.all().order_by('order', 'date'),
    }
    return render(request, "portal/sessions/session_list.html", context)


@login_required(login_url="/accounts/login/")
def session_manage(request, event_pk, agenda_pk, session_pk=None):
    """Create or update a session within an agenda"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)
    session = None

    if session_pk:
        session = get_object_or_404(Session, pk=session_pk, agenda=agenda)

    if request.method == "POST":
        form = SessionForm(request.POST, instance=session, agenda=agenda)
        if form.is_valid():
            session = form.save(commit=False)
            session.agenda = agenda

            # Handle allow_registration checkbox explicitly
            # If checkbox is not in POST data, it means it was unchecked
            session.allow_registration = request.POST.get('allow_registration') == 'true'

            # Handle slots_available
            slots_available = request.POST.get('slots_available', '').strip()
            if slots_available:
                try:
                    session.slots_available = int(slots_available)
                except (ValueError, TypeError):
                    session.slots_available = None
            else:
                session.slots_available = None

            # Handle payment settings
            session.is_paid_session = request.POST.get('is_paid_session') == 'true'

            # Handle session_fee
            session_fee = request.POST.get('session_fee', '0').strip()
            try:
                session.session_fee = float(session_fee) if session_fee else 0
            except (ValueError, TypeError):
                session.session_fee = 0

            # Handle payment_methods (checkboxes return a list)
            payment_methods = request.POST.getlist('payment_methods')
            session.payment_methods = payment_methods if payment_methods else []

            session.save()
            form.save_m2m()  # Save many-to-many relationships

            if session_pk:
                messages.success(request, "Session updated successfully!")
            else:
                messages.success(request, "Session created successfully!")

            # Check for next parameter to redirect properly
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('portal:agenda_session_list', event_pk=event.pk, agenda_pk=agenda.pk)
    else:
        form = SessionForm(instance=session, agenda=agenda)

    # Get all speakers to show in the selection
    speakers = Speaker.objects.all()

    context = {
        'event': event,
        'agenda': agenda,
        'session': session,
        'form': form,
        'session_types': Session.SESSION_TYPES,
        'speakers': speakers,
    }
    return render(request, "portal/sessions/session_form.html", context)


@login_required(login_url="/accounts/login/")
def session_delete(request, event_pk, agenda_pk, session_pk):
    """Delete a session"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)
    session = get_object_or_404(Session, pk=session_pk, agenda=agenda)

    if request.method == "POST":
        session_title = session.title
        session.delete()
        messages.success(request, f"Session '{session_title}' deleted successfully!")
        return redirect('portal:session_list', event_pk=event.pk)

    context = {
        'event': event,
        'agenda': agenda,
        'session': session,
    }
    return render(request, "portal/sessions/session_confirm_delete.html", context)


@login_required(login_url="/accounts/login/")
def session_move_up(request, event_pk, agenda_pk, session_pk):
    """Move session up in order within an agenda"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)
    session = get_object_or_404(Session, pk=session_pk, agenda=agenda)

    # Find the session with the next earlier start time in the same agenda
    previous_session = Session.objects.filter(
        agenda=agenda,
        start_time__lt=session.start_time
    ).order_by('-start_time').first()

    if previous_session:
        # Swap start and end times
        session_start = session.start_time
        session_end = session.end_time
        previous_start = previous_session.start_time
        previous_end = previous_session.end_time

        session.start_time = previous_start
        session.end_time = previous_end
        previous_session.start_time = session_start
        previous_session.end_time = session_end

        session.save()
        previous_session.save()

        messages.success(request, f"Session '{session.title}' moved up!")

    # Handle redirect
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('portal:session_list', event_pk=event.pk)


@login_required(login_url="/accounts/login/")
def session_move_down(request, event_pk, agenda_pk, session_pk):
    """Move session down in order within an agenda"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)
    session = get_object_or_404(Session, pk=session_pk, agenda=agenda)

    # Find the session with the next later start time in the same agenda
    next_session = Session.objects.filter(
        agenda=agenda,
        start_time__gt=session.start_time
    ).order_by('start_time').first()

    if next_session:
        # Swap start and end times
        session_start = session.start_time
        session_end = session.end_time
        next_start = next_session.start_time
        next_end = next_session.end_time

        session.start_time = next_start
        session.end_time = next_end
        next_session.start_time = session_start
        next_session.end_time = session_end

        session.save()
        next_session.save()

        messages.success(request, f"Session '{session.title}' moved down!")

    # Handle redirect
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('portal:session_list', event_pk=event.pk)


@login_required(login_url="/accounts/login/")
def session_move_ajax(request, event_pk):
    """AJAX endpoint for moving sessions"""
    if request.method == "POST":
        event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
        agenda_pk = request.POST.get('agenda_pk')
        session_pk = request.POST.get('session_pk')
        direction = request.POST.get('direction')

        agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)
        session = get_object_or_404(Session, pk=session_pk, agenda=agenda)

        # Get all sessions in this agenda ordered by order field
        sessions = list(Session.objects.filter(agenda=agenda).order_by('order', 'start_time'))

        try:
            current_index = sessions.index(session)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Session not found in agenda.'})

        if direction == 'up':
            if current_index > 0:
                # Swap with previous session
                previous_session = sessions[current_index - 1]

                # Swap order values
                session_order = session.order
                previous_order = previous_session.order

                session.order = previous_order
                previous_session.order = session_order

                session.save()
                previous_session.save()

                return JsonResponse({'success': True, 'message': f"Session '{session.title}' moved up!"})

        elif direction == 'down':
            if current_index < len(sessions) - 1:
                # Swap with next session
                next_session = sessions[current_index + 1]

                # Swap order values
                session_order = session.order
                next_order = next_session.order

                session.order = next_order
                next_session.order = session_order

                session.save()
                next_session.save()

                return JsonResponse({'success': True, 'message': f"Session '{session.title}' moved down!"})

        return JsonResponse({'success': False, 'message': 'Unable to move session in that direction.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required(login_url="/accounts/login/")
def session_registrations(request, event_pk, agenda_pk, session_pk):
    """View and manage registrations for a session"""
    from src.api.models import SessionRegistration

    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    agenda = get_object_or_404(Agenda, pk=agenda_pk, event=event)
    session = get_object_or_404(Session, pk=session_pk, agenda=agenda)

    # Get all registrations for this session
    registrations = SessionRegistration.objects.filter(session=session).select_related('user')

    # Handle unregistration if requested
    if request.method == "POST":
        registration_pk = request.POST.get('registration_pk')
        if registration_pk:
            registration = get_object_or_404(SessionRegistration, pk=registration_pk, session=session)
            user_name = registration.user.get_full_name() or registration.user.username
            registration.delete()
            messages.success(request, f"Removed {user_name} from session registration.")
            return redirect('portal:session_registrations', event_pk=event.pk, agenda_pk=agenda.pk, session_pk=session.pk)

    context = {
        'event': event,
        'agenda': agenda,
        'session': session,
        'registrations': registrations,
        'total_registrations': registrations.count(),
        'slots_remaining': (session.slots_available - registrations.count()) if session.slots_available else None,
    }
    return render(request, "portal/sessions/session_registrations.html", context)


# EXHIBITION AREA MANAGEMENT
@login_required(login_url="/accounts/login/")
def exhibition_areas(request, event_pk):
    """Manage exhibition areas for an event"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    areas = event.exhibition_areas.all()
    exhibitors = event.exhibitors.all()

    context = {
        'event': event,
        'areas': areas,
        'exhibitors': exhibitors,
    }
    return render(request, "portal/exhibition/areas.html", context)


@login_required(login_url="/accounts/login/")
def exhibition_area_create(request, event_pk, area_pk=None):
    """Create or update exhibition area"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    area = None

    if area_pk:
        area = get_object_or_404(ExhibitionArea, pk=area_pk, event=event)

    if request.method == "POST":
        form = ExhibitionAreaForm(request.POST, request.FILES, instance=area)
        if form.is_valid():
            area = form.save(commit=False)
            area.event = event
            area.save()

            if area_pk:
                messages.success(request, f"Exhibition area '{area.name}' updated!")
            else:
                messages.success(request, f"Exhibition area '{area.name}' created!")
            return redirect('portal:exhibition_areas', event_pk=event.pk)
    else:
        form = ExhibitionAreaForm(instance=area)

    context = {
        'event': event,
        'area': area,
        'form': form,
    }
    return render(request, "portal/exhibition/area_form.html", context)


@login_required(login_url="/accounts/login/")
def exhibitor_applications(request, event_pk):
    """View and manage exhibitor applications"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    exhibitors = event.exhibitors.all()

    if request.method == "POST":
        exhibitor_id = request.POST.get('exhibitor_id')
        action = request.POST.get('action')

        exhibitor = get_object_or_404(Exhibitor, pk=exhibitor_id, event=event)

        if action == 'approve':
            exhibitor.approved = True
            exhibitor.save()
            messages.success(request, f"Exhibitor {exhibitor.company_name} approved!")
        elif action == 'reject':
            exhibitor.approved = False
            exhibitor.save()
            messages.warning(request, f"Exhibitor {exhibitor.company_name} rejected.")

    context = {
        'event': event,
        'exhibitors': exhibitors,
        'pending': exhibitors.filter(approved=False),
        'approved': exhibitors.filter(approved=True),
    }
    return render(request, "portal/exhibition/applications.html", context)


# EVENT PUBLISHING
@login_required(login_url="/accounts/login/")
def event_publish(request, pk):
    """Publish an event to make it visible to attendees"""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if request.method == "POST":
        if event.status == 'draft':
            event.publish()
            messages.success(request, f"Event '{event.title}' has been published!")
        else:
            messages.warning(request, f"Event is already {event.status}")

        return redirect(reverse('portal:event_detail', kwargs={'pk': event.pk}) + '#tab-maps')

    # Check if event is ready to publish
    ready_to_publish = True
    missing_items = []

    # Check if event has sessions through agendas
    has_sessions = False
    for agenda in event.agendas.all():
        if agenda.sessions.exists():
            has_sessions = True
            break
    if not has_sessions:
        ready_to_publish = False
        missing_items.append("At least one session/agenda item")

    context = {
        'event': event,
        'ready_to_publish': ready_to_publish,
        'missing_items': missing_items,
        'has_sessions': has_sessions,
    }
    return render(request, "portal/events/event_publish.html", context)


# CONFERENCE DASHBOARD & FEATURES
@login_required(login_url="/accounts/login/")
def conference_dashboard(request, event_pk):
    """Conference dashboard with real-time features"""
    from src.api.models import SessionBookmark, Notification, CheckInLog
    from datetime import timedelta
    from django.db.models import Count, Q

    event = get_object_or_404(Event, pk=event_pk)

    # Ticket system removed - set to None
    user_ticket = None

    # Get upcoming sessions (within next 3 hours)
    now = timezone.now()
    upcoming_sessions = Session.objects.filter(
        agenda__event=event,
        start_time__gte=now,
        start_time__lte=now + timedelta(hours=3)
    ).order_by('start_time')[:5]

    # Add time until session starts
    for session in upcoming_sessions:
        time_diff = session.start_time - now
        session.time_until = int(time_diff.total_seconds() / 60)  # minutes

    # Get user's bookmarked sessions
    bookmarked_sessions = SessionBookmark.objects.filter(
        user=request.user,
        session__event=event
    ).values_list('session_id', flat=True)

    my_bookmarks = SessionBookmark.objects.filter(
        user=request.user,
        session__event=event
    ).select_related('session')

    # Get notifications
    notifications = Notification.objects.filter(
        user=request.user,
        event=event,
        is_read=False
    )[:5]

    # Get exhibition info
    exhibition_areas = event.exhibition_areas.all()
    exhibitors = event.exhibitors.filter(approved=True)

    # Calculate stats
    total_attendees = event.registrations.filter(status='confirmed').count()
    # Ticket system removed - set default values
    checked_in_count = 0
    checked_in_percentage = 0

    # Get unique speakers count
    speakers_count = Speaker.objects.filter(sessions__agenda__event=event).distinct().count()

    # Calculate event days
    session_days = 1
    if event.end_date:
        session_days = (event.end_date.date() - event.date.date()).days + 1

    context = {
        'event': event,
        'user_ticket': user_ticket,
        'upcoming_sessions': upcoming_sessions,
        'bookmarked_sessions': list(bookmarked_sessions),
        'my_bookmarks': my_bookmarks,
        'notifications': notifications,
        'exhibition_areas': exhibition_areas,
        'exhibitors': exhibitors,
        'total_attendees': total_attendees,
        'checked_in_count': checked_in_count,
        'checked_in_percentage': int(checked_in_percentage),
        'speakers_count': speakers_count,
        'session_days': session_days,
    }
    return render(request, "portal/conference/dashboard.html", context)


@login_required(login_url="/accounts/login/")
def toggle_bookmark(request, event_pk, session_pk):
    """Toggle session bookmark"""
    from src.api.models import SessionBookmark

    if request.method == "POST":
        session = get_object_or_404(Session, pk=session_pk, event_id=event_pk)
        bookmark, created = SessionBookmark.objects.get_or_create(
            user=request.user,
            session=session
        )

        if not created:
            bookmark.delete()
            bookmarked = False
        else:
            bookmarked = True

        return JsonResponse({'success': True, 'bookmarked': bookmarked})

    return JsonResponse({'success': False})


@login_required(login_url="/accounts/login/")
def toggle_agenda_like(request, event_pk, agenda_pk):
    """Toggle agenda like"""
    from src.api.models import AgendaLike

    if request.method == "POST":
        agenda = get_object_or_404(Agenda, pk=agenda_pk, event_id=event_pk)
        like, created = AgendaLike.objects.get_or_create(
            user=request.user,
            agenda=agenda
        )

        if not created:
            like.delete()
            liked = False
        else:
            liked = True

        return JsonResponse({'success': True, 'liked': liked, 'total_likes': agenda.likes.count()})

    return JsonResponse({'success': False})


@login_required(login_url="/accounts/login/")
# Check-in function removed with ticket system


@login_required(login_url="/accounts/login/")
def upcoming_sessions_api(request, event_pk):
    """API endpoint for upcoming sessions"""
    from datetime import timedelta

    event = get_object_or_404(Event, pk=event_pk)
    now = timezone.now()

    sessions = Session.objects.filter(
        agenda__event=event,
        start_time__gte=now,
        start_time__lte=now + timedelta(hours=1)
    ).values('id', 'title', 'start_time', 'location')

    sessions_data = []
    for session in sessions:
        time_diff = session['start_time'] - now
        minutes_until = int(time_diff.total_seconds() / 60)
        sessions_data.append({
            'id': session['id'],
            'title': session['title'],
            'location': session['location'],
            'minutes_until': minutes_until
        })

    return JsonResponse({'sessions': sessions_data})


@login_required(login_url="/accounts/login/")
def agenda_qr_code(request, pk):
    """Generate and download QR code for event agenda"""
    from django.http import HttpResponse
    from src.api.utils import generate_agenda_qr_code

    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    # Generate QR code
    qr_file = generate_agenda_qr_code(event)

    # Return as downloadable file
    response = HttpResponse(qr_file.read(), content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="agenda_qr_{event.title.replace(" ", "_")}.png"'

    return response


@login_required(login_url="/accounts/login/")
def registration_qr_code(request, pk):
    """Generate and download QR code for event registration"""
    from django.http import HttpResponse
    from src.api.utils import generate_registration_qr_code

    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    # Generate QR code
    qr_file = generate_registration_qr_code(event, request)

    # Return as downloadable file
    response = HttpResponse(qr_file.read(), content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="registration_qr_{event.title.replace(" ", "_")}.png"'

    return response


@login_required(login_url="/accounts/login/")
def registration_qr_display(request, pk):
    """Display QR code for event registration in popup"""
    import base64
    from src.api.utils import generate_registration_qr_code

    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    # Generate QR code
    qr_file = generate_registration_qr_code(event, request)

    # Convert to base64 for display
    qr_file.seek(0)
    qr_base64 = base64.b64encode(qr_file.read()).decode('utf-8')

    # Create registration URL
    registration_url = f"{request.scheme}://{request.get_host()}/register/{event.id}/"

    context = {
        'event': event,
        'qr_base64': qr_base64,
        'registration_url': registration_url,
    }

    return JsonResponse(context)


def self_register(request, pk):
    """Self-registration page for attendees (no login required)"""
    # Redirect to external form for event ID 1
    if pk == 1:
        return redirect('https://bankintegration.technospyre.com/CombineRegistrationForm')

    event = get_object_or_404(Event, pk=pk, status='published')

    # Helper function to get client IP
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    # Log page visit
    from src.api.models import RegistrationLog
    RegistrationLog.objects.create(
        event=event,
        action='page_visit',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )

    # Check if event is still accepting registrations
    available_spots = event.max_attendees - event.registrations.filter(status="confirmed").count()

    if request.method == "POST":
        from src.api.forms import SelfRegistrationForm
        from src.api.models import EventRegistrationType

        form = SelfRegistrationForm(request.POST, event=event)

        if available_spots <= 0:
            messages.error(request, "Sorry, this event is full.")
            return redirect('self_register', pk=pk)

        if form.is_valid():
            # Get form data
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            phone_number = form.cleaned_data['phone_number']
            designation = form.cleaned_data.get('designation', '')
            affiliations = form.cleaned_data.get('affiliations', '')
            address = form.cleaned_data.get('address', '')
            country = form.cleaned_data.get('country', '')
            registration_type_id = form.cleaned_data.get('registration_type')
            workshop_ids = form.cleaned_data.get('workshops', [])

            # Log form started
            RegistrationLog.objects.create(
                event=event,
                action='form_started',
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )

            # Create or get user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone_number': phone_number,
                    'designation': designation,
                    'affiliations': affiliations,
                    'address': address,
                    'country': country,
                }
            )

            # Update user info if not created (user already exists)
            if not created:
                user.first_name = first_name
                user.last_name = last_name
                user.phone_number = phone_number
                if designation:
                    user.designation = designation
                if affiliations:
                    user.affiliations = affiliations
                if address:
                    user.address = address
                if country:
                    user.country = country
                user.save()

            # Check if already registered
            if Registration.objects.filter(event=event, user=user).exists():
                messages.warning(request, "You are already registered for this event.")
                return render(request, "portal/events/self_register.html", {
                    "event": event,
                    "form": form,
                    "available_spots": available_spots
                })

            # Get registration type if provided
            registration_type = None
            if registration_type_id:
                try:
                    registration_type = EventRegistrationType.objects.get(id=registration_type_id, event=event)
                except EventRegistrationType.DoesNotExist:
                    pass

            # Create registration
            registration = Registration.objects.create(
                event=event,
                user=user,
                status="confirmed",
                registration_type=registration_type,
                designation=designation,
                affiliations=affiliations,
                address=address,
                country=country,
                phone_number=phone_number,
            )

            # Add selected workshops
            if workshop_ids:
                workshops = Session.objects.filter(
                    id__in=workshop_ids,
                    agenda__event=event,
                    session_type='workshop'
                )
                registration.selected_workshops.set(workshops)

            # Log successful registration (free event)
            RegistrationLog.objects.create(
                event=event,
                user=user,
                registration=registration,
                action='registration_completed',
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                registration_type=registration_type,
                payment_method='none',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                notes='Free registration completed successfully'
            )

            messages.success(request, f"Successfully registered for {event.title}!")
            return render(request, "portal/events/registration_success.html", {
                "event": event,
                "user": user,
                "registration": registration
            })
        else:
            # Form has errors
            messages.error(request, "Please correct the errors in the form.")
    else:
        # GET request - create empty form
        from src.api.forms import SelfRegistrationForm
        form = SelfRegistrationForm(event=event)

    # Get active APK for download button
    from src.api.models import AppDownload, EventRegistrationType
    active_apk = AppDownload.objects.filter(is_active=True).first()

    # Get workshop sessions with fees for JavaScript cost calculation
    workshop_sessions = Session.objects.filter(
        agenda__event=event,
        session_type='workshop'
    ).values('id', 'title', 'is_paid_session', 'session_fee', 'start_time', 'end_time', 'location')

    # Convert Decimal to float and time to string for JSON serialization
    workshop_sessions_list = []
    for ws in workshop_sessions:
        ws_dict = dict(ws)
        if ws_dict['session_fee'] is not None:
            ws_dict['session_fee'] = float(ws_dict['session_fee'])
        # Convert time fields to strings
        if ws_dict['start_time']:
            ws_dict['start_time'] = ws_dict['start_time'].strftime('%H:%M')
        if ws_dict['end_time']:
            ws_dict['end_time'] = ws_dict['end_time'].strftime('%H:%M')
        workshop_sessions_list.append(ws_dict)

    # Get registration types with fees for JavaScript cost calculation
    registration_types = EventRegistrationType.objects.filter(
        event=event,
        is_active=True
    ).values('id', 'name', 'is_paid', 'amount').order_by('order')

    # Convert Decimal to float for JSON serialization
    registration_types_list = []
    for rt in registration_types:
        rt_dict = dict(rt)
        if rt_dict['amount'] is not None:
            rt_dict['amount'] = float(rt_dict['amount'])
        registration_types_list.append(rt_dict)

    context = {
        "event": event,
        "form": form,
        "available_spots": available_spots,
        "app": active_apk,
        "workshop_sessions_json": json.dumps(workshop_sessions_list),
        "registration_types_json": json.dumps(registration_types_list),
    }
    return render(request, "portal/events/self_register.html", context)


# NOTIFICATION API ENDPOINTS
@login_required(login_url="/accounts/login/")
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    if request.method == 'POST':
        from src.api.models import Notification
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            return JsonResponse({'success': True, 'message': 'Notification marked as read'})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Notification not found'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url="/accounts/login/")
def mark_all_notifications_read(request):
    """Mark all notifications as read for the current user"""
    if request.method == 'POST':
        from src.api.models import Notification
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True, 'message': 'All notifications marked as read'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url="/accounts/login/")
def archive_all_notifications(request):
    """Archive all notifications for the current user"""
    if request.method == 'POST':
        from src.api.models import Notification
        Notification.objects.filter(user=request.user).delete()
        return JsonResponse({'success': True, 'message': 'All notifications archived'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url="/accounts/login/")
def notification_count(request):
    """Get unread notification count for the current user"""
    from src.api.models import Notification
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


@login_required(login_url="/accounts/login/")
def session_speakers_api(request, session_pk):
    """API for managing speakers for a session"""
    session = get_object_or_404(Session, pk=session_pk, agenda__event__organizer=request.user)

    if request.method == 'GET':
        # Return current speakers for this session and all available speakers
        session_speakers = list(session.speakers.values('id', 'name', 'title', 'company', 'photo'))
        all_speakers = list(Speaker.objects.values('id', 'name', 'title', 'company', 'photo'))

        return JsonResponse({
            'session_speakers': session_speakers,
            'all_speakers': all_speakers
        })

    elif request.method == 'POST':
        # Update speakers for this session
        try:
            data = json.loads(request.body)
            speaker_ids = data.get('speakers', [])

            # Clear existing speakers and add new ones
            session.speakers.clear()
            if speaker_ids:
                speakers = Speaker.objects.filter(id__in=speaker_ids)
                session.speakers.set(speakers)

            return JsonResponse({
                'success': True,
                'message': 'Speakers updated successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url="/accounts/login/")
def event_sessions_api(request, event_pk):
    """API endpoint to get all sessions for an event"""
    event = get_object_or_404(Event, pk=event_pk)

    # Get all sessions for all agendas of this event
    sessions = Session.objects.filter(agenda__event=event).values(
        'id', 'title', 'session_type', 'start_time', 'end_time', 'location'
    )

    # Format time fields
    sessions_list = []
    for session in sessions:
        session_dict = dict(session)
        if session_dict['start_time']:
            session_dict['start_time'] = session_dict['start_time'].strftime('%H:%M')
        if session_dict['end_time']:
            session_dict['end_time'] = session_dict['end_time'].strftime('%H:%M')
        sessions_list.append(session_dict)

    return JsonResponse(sessions_list, safe=False)


@login_required(login_url="/accounts/login/")
def material_sessions_api(request, material_pk):
    """API endpoint to get sessions associated with a supporting material"""
    material = get_object_or_404(SupportingMaterial, pk=material_pk)

    # Check permission
    if material.event.organizer != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    sessions = material.sessions.values('id', 'title')
    return JsonResponse(list(sessions), safe=False)


# Global Speaker Management Views
@login_required(login_url="/accounts/login/")
def speaker_list_global(request):
    """List all speakers globally"""
    speakers = Speaker.objects.all().order_by('name')
    context = {
        'speakers': speakers,
    }
    return render(request, "portal/speakers/speaker_list_global.html", context)


@login_required(login_url="/accounts/login/")
def speaker_create_global(request):
    """Create a new speaker globally"""
    if request.method == "POST":
        form = SpeakerForm(request.POST, request.FILES)
        if form.is_valid():
            speaker = form.save()
            messages.success(request, f"Speaker {speaker.name} created successfully!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('portal:speaker_list_global')
    else:
        form = SpeakerForm()

    context = {
        'form': form,
        'speaker': None,
    }
    return render(request, "portal/speakers/speaker_form_global.html", context)


@login_required(login_url="/accounts/login/")
def speaker_edit_global(request, speaker_pk):
    """Edit an existing speaker globally"""
    speaker = get_object_or_404(Speaker, pk=speaker_pk)

    if request.method == "POST":
        form = SpeakerForm(request.POST, request.FILES, instance=speaker)
        if form.is_valid():
            speaker = form.save()
            messages.success(request, f"Speaker {speaker.name} updated successfully!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('portal:speaker_list_global')
    else:
        form = SpeakerForm(instance=speaker)

    context = {
        'form': form,
        'speaker': speaker,
    }
    return render(request, "portal/speakers/speaker_form_global.html", context)


@login_required(login_url="/accounts/login/")
def speaker_delete_global(request, speaker_pk):
    """Delete a speaker globally"""
    speaker = get_object_or_404(Speaker, pk=speaker_pk)

    if request.method == "POST":
        speaker_name = speaker.name
        speaker.delete()
        messages.success(request, f"Speaker {speaker_name} deleted successfully!")
        return redirect('portal:speaker_list_global')

    context = {
        'speaker': speaker,
    }
    return render(request, "portal/speakers/speaker_delete_global.html", context)


# Venue Map Views
@login_required(login_url="/accounts/login/")
def venue_map_create(request, event_pk):
    """Create a new venue map for an event"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)

    if request.method == "POST":
        form = VenueMapForm(request.POST, request.FILES)
        if form.is_valid():
            venue_map = form.save(commit=False)
            venue_map.event = event
            venue_map.save()
            messages.success(request, f"Venue map '{venue_map.title}' created successfully!")
            return redirect(reverse('portal:event_detail', kwargs={'pk': event.pk}) + '#tab-maps')
    else:
        form = VenueMapForm()

    context = {
        'form': form,
        'event': event,
        'action': 'Create'
    }
    return render(request, "portal/events/venue_map_form.html", context)


@login_required(login_url="/accounts/login/")
def venue_map_edit(request, event_pk, map_pk):
    """Edit an existing venue map"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    venue_map = get_object_or_404(VenueMap, pk=map_pk, event=event)

    if request.method == "POST":
        form = VenueMapForm(request.POST, request.FILES, instance=venue_map)
        if form.is_valid():
            venue_map = form.save()
            messages.success(request, f"Venue map '{venue_map.title}' updated successfully!")
            return redirect(reverse('portal:event_detail', kwargs={'pk': event.pk}) + '#tab-maps')
    else:
        form = VenueMapForm(instance=venue_map)

    context = {
        'form': form,
        'event': event,
        'venue_map': venue_map,
        'action': 'Edit'
    }
    return render(request, "portal/events/venue_map_form.html", context)


@login_required(login_url="/accounts/login/")
def venue_map_delete(request, event_pk, map_pk):
    """Delete a venue map"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    venue_map = get_object_or_404(VenueMap, pk=map_pk, event=event)

    if request.method == "POST":
        map_title = venue_map.title
        venue_map.delete()
        messages.success(request, f"Venue map '{map_title}' deleted successfully!")
        return redirect(reverse('portal:event_detail', kwargs={'pk': event.pk}) + '#tab-maps')

    context = {
        'event': event,
        'venue_map': venue_map,
    }
    return render(request, "portal/events/venue_map_delete.html", context)


# ===============================
# SPONSOR MANAGEMENT VIEWS
# ===============================

@login_required(login_url="/accounts/login/")
def sponsor_list_global(request):
    """List all sponsors globally"""
    sponsors = Sponsor.objects.all().order_by('title')
    context = {
        'sponsors': sponsors,
    }
    return render(request, "portal/sponsors/sponsor_list.html", context)


@login_required(login_url="/accounts/login/")
def sponsor_create_global(request):
    """Create a new sponsor globally"""
    if request.method == "POST":
        form = SponsorForm(request.POST, request.FILES)
        if form.is_valid():
            sponsor = form.save()
            messages.success(request, f"Sponsor '{sponsor.title}' created successfully!")
            return redirect('portal:sponsor_list_global')
    else:
        form = SponsorForm()

    context = {
        'form': form,
        'action': 'Create'
    }
    return render(request, "portal/sponsors/sponsor_form.html", context)


@login_required(login_url="/accounts/login/")
def sponsor_edit_global(request, sponsor_pk):
    """Edit an existing sponsor globally"""
    sponsor = get_object_or_404(Sponsor, pk=sponsor_pk)

    if request.method == "POST":
        form = SponsorForm(request.POST, request.FILES, instance=sponsor)
        if form.is_valid():
            sponsor = form.save()
            messages.success(request, f"Sponsor '{sponsor.title}' updated successfully!")
            return redirect('portal:sponsor_list_global')
    else:
        form = SponsorForm(instance=sponsor)

    context = {
        'form': form,
        'sponsor': sponsor,
        'action': 'Edit'
    }
    return render(request, "portal/sponsors/sponsor_form.html", context)


@login_required(login_url="/accounts/login/")
def sponsor_delete_global(request, sponsor_pk):
    """Delete a sponsor globally"""
    sponsor = get_object_or_404(Sponsor, pk=sponsor_pk)

    if request.method == "POST":
        sponsor_title = sponsor.title
        sponsor.delete()
        messages.success(request, f"Sponsor '{sponsor_title}' deleted successfully!")
        return redirect('portal:sponsor_list_global')

    context = {
        'sponsor': sponsor,
    }
    return render(request, "portal/sponsors/sponsor_delete.html", context)


@login_required(login_url="/accounts/login/")
def event_sponsors_manage(request, event_pk):
    """Manage sponsors for a specific event"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    event_sponsors = event.sponsors.all()
    all_sponsors = Sponsor.objects.all()

    context = {
        'event': event,
        'event_sponsors': event_sponsors,
        'all_sponsors': all_sponsors,
    }
    return render(request, "portal/events/event_sponsors.html", context)


@login_required(login_url="/accounts/login/")
def event_sponsors_api(request, event_pk):
    """API endpoint for managing event sponsors"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)

    if request.method == 'GET':
        # Return current sponsors and all available sponsors
        event_sponsors = event.sponsors.all()
        all_sponsors = Sponsor.objects.all()

        return JsonResponse({
            'success': True,
            'event_sponsors': [
                {
                    'id': sponsor.id,
                    'title': sponsor.title,
                    'description': sponsor.description,
                    'logo': sponsor.logo.url if sponsor.logo else None,
                    'website': sponsor.website,
                    'email': sponsor.email,
                    'phone': sponsor.phone,
                }
                for sponsor in event_sponsors
            ],
            'all_sponsors': [
                {
                    'id': sponsor.id,
                    'title': sponsor.title,
                    'description': sponsor.description,
                    'logo': sponsor.logo.url if sponsor.logo else None,
                    'website': sponsor.website,
                    'email': sponsor.email,
                    'phone': sponsor.phone,
                }
                for sponsor in all_sponsors
            ]
        })

    elif request.method == 'POST':
        # Update event sponsors
        try:
            data = json.loads(request.body)
            sponsor_ids = data.get('sponsors', [])

            # Clear current sponsors and set new ones
            event.sponsors.clear()
            if sponsor_ids:
                sponsors = Sponsor.objects.filter(id__in=sponsor_ids)
                event.sponsors.set(sponsors)

            return JsonResponse({
                'success': True,
                'message': 'Event sponsors updated successfully!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error updating sponsors: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


# ===============================
# SUPPORTING MATERIALS MANAGEMENT VIEWS
# ===============================

@login_required(login_url="/accounts/login/")
def supporting_material_create(request, event_pk):
    """Create a supporting material for an event"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)

    if request.method == 'POST':
        form = SupportingMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.event = event
            material.uploaded_by = request.user
            material.save()

            # Save many-to-many relationships (sessions)
            form.save_m2m()

            # Also handle sessions from POST if not using form widget
            session_ids = request.POST.getlist('sessions')
            if session_ids:
                material.sessions.set(session_ids)

            messages.success(request, f"Supporting material '{material.title}' uploaded successfully!")
            return redirect(reverse('portal:event_detail', kwargs={'pk': event.pk}) + '#tab-materials')
    else:
        form = SupportingMaterialForm()
        # Limit sessions to this event's sessions
        form.fields['sessions'].queryset = Session.objects.filter(agenda__event=event)

    context = {
        'form': form,
        'event': event,
        'action': 'Add'
    }
    return render(request, "portal/events/material_form.html", context)


@login_required(login_url="/accounts/login/")
def supporting_material_edit(request, event_pk, material_pk):
    """Edit a supporting material"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    material = get_object_or_404(SupportingMaterial, pk=material_pk, event=event)

    if request.method == 'POST':
        form = SupportingMaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            material = form.save()

            # Handle sessions from POST if not using form widget
            session_ids = request.POST.getlist('sessions')
            if session_ids:
                material.sessions.set(session_ids)
            elif 'sessions' in request.POST:
                # Clear sessions if none selected
                material.sessions.clear()

            messages.success(request, f"Supporting material '{material.title}' updated successfully!")
            return redirect(reverse('portal:event_detail', kwargs={'pk': event.pk}) + '#tab-materials')
    else:
        form = SupportingMaterialForm(instance=material)
        # Limit sessions to this event's sessions
        form.fields['sessions'].queryset = Session.objects.filter(agenda__event=event)

    context = {
        'form': form,
        'event': event,
        'material': material,
        'action': 'Edit'
    }
    return render(request, "portal/events/material_form.html", context)


@login_required(login_url="/accounts/login/")
def supporting_material_delete(request, event_pk, material_pk):
    """Delete a supporting material"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    material = get_object_or_404(SupportingMaterial, pk=material_pk, event=event)

    if request.method == 'POST':
        material_title = material.title
        # Delete the file from storage
        if material.file:
            material.file.delete(save=False)
        material.delete()
        messages.success(request, f"Supporting material '{material_title}' deleted successfully!")
        return redirect(reverse('portal:event_detail', kwargs={'pk': event.pk}) + '#tab-materials')

    context = {
        'event': event,
        'material': material,
    }
    return render(request, "portal/events/material_delete.html", context)


@login_required(login_url="/accounts/login/")
def supporting_material_api(request, event_pk):
    """API endpoint for managing supporting materials via AJAX"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)

    if request.method == 'POST':
        try:
            form = SupportingMaterialForm(request.POST, request.FILES)
            if form.is_valid():
                material = form.save(commit=False)
                material.event = event
                material.uploaded_by = request.user
                material.save()

                return JsonResponse({
                    'success': True,
                    'message': f"Supporting material '{material.title}' uploaded successfully!",
                    'material': {
                        'id': material.id,
                        'title': material.title,
                        'description': material.description,
                        'material_type': material.material_type,
                        'material_type_display': material.get_material_type_display(),
                        'file_url': material.file.url if material.file else None,
                        'file_size_display': material.get_file_size_display(),
                        'file_extension': material.get_file_extension(),
                        'is_public': material.is_public,
                        'created_at': material.created_at.strftime('%M %j, %Y'),
                    }
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Please check the form data.',
                    'errors': form.errors
                })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error uploading material: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


# ANNOUNCEMENTS VIEWS
@login_required(login_url="/accounts/login/")
def announcements(request):
    """List all announcements created by the current user"""
    from src.api.models import Announcement
    announcements = Announcement.objects.filter(author=request.user).select_related('event')

    # Apply filters
    event_filter = request.GET.get('event')
    if event_filter:
        announcements = announcements.filter(event_id=event_filter)

    type_filter = request.GET.get('type')
    if type_filter:
        announcements = announcements.filter(type=type_filter)

    priority_filter = request.GET.get('priority')
    if priority_filter:
        announcements = announcements.filter(priority=priority_filter)

    # Search
    search_query = request.GET.get('search')
    if search_query:
        from django.db.models import Q
        announcements = announcements.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query)
        )

    # Get user's events for filter dropdown
    user_events = Event.objects.filter(organizer=request.user)

    context = {
        'announcements': announcements,
        'user_events': user_events,
    }
    return render(request, 'portal/announcements/announcements.html', context)


@login_required(login_url="/accounts/login/")
def announcement_create(request):
    """Create a new announcement"""
    from src.api.models import Announcement

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        type = request.POST.get('type', 'general')
        event_id = request.POST.get('event')
        priority = request.POST.get('priority', 'medium')
        publish_date = request.POST.get('publish_date')
        expire_date = request.POST.get('expire_date')

        # Validation
        if not title or not content:
            messages.error(request, 'Title and content are required.')
            return redirect('portal:announcement_create')

        # Create announcement
        announcement = Announcement(
            title=title,
            content=content,
            type=type,
            priority=priority,
            author=request.user
        )

        # Set event if event-specific
        if type == 'event_specific' and event_id:
            try:
                event = Event.objects.get(id=event_id, organizer=request.user)
                announcement.event = event
            except Event.DoesNotExist:
                messages.error(request, 'Selected event not found.')
                return redirect('portal:announcement_create')

        # Set dates
        if publish_date:
            try:
                announcement.publish_date = timezone.datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
            except:
                pass

        if expire_date:
            try:
                announcement.expire_date = timezone.datetime.fromisoformat(expire_date.replace('Z', '+00:00'))
            except:
                pass

        announcement.save()
        messages.success(request, 'Announcement created successfully!')
        return redirect('portal:announcements')

    # Get user's events for the form
    user_events = Event.objects.filter(organizer=request.user)
    context = {'user_events': user_events}
    return render(request, 'portal/announcements/announcement_form.html', context)


@login_required(login_url="/accounts/login/")
def announcement_update(request, pk):
    """Update an existing announcement"""
    from src.api.models import Announcement
    announcement = get_object_or_404(Announcement, pk=pk, author=request.user)

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        type = request.POST.get('type', 'general')
        event_id = request.POST.get('event')
        priority = request.POST.get('priority', 'medium')
        publish_date = request.POST.get('publish_date')
        expire_date = request.POST.get('expire_date')
        is_active = request.POST.get('is_active') == 'on'

        # Validation
        if not title or not content:
            messages.error(request, 'Title and content are required.')
            return redirect('portal:announcement_update', pk=pk)

        # Update announcement
        announcement.title = title
        announcement.content = content
        announcement.type = type
        announcement.priority = priority
        announcement.is_active = is_active

        # Set event if event-specific
        if type == 'event_specific' and event_id:
            try:
                event = Event.objects.get(id=event_id, organizer=request.user)
                announcement.event = event
            except Event.DoesNotExist:
                messages.error(request, 'Selected event not found.')
                return redirect('portal:announcement_update', pk=pk)
        else:
            announcement.event = None

        # Set dates
        if publish_date:
            try:
                announcement.publish_date = timezone.datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
            except:
                pass

        if expire_date:
            try:
                announcement.expire_date = timezone.datetime.fromisoformat(expire_date.replace('Z', '+00:00'))
            except:
                pass
        else:
            announcement.expire_date = None

        announcement.save()
        messages.success(request, 'Announcement updated successfully!')
        return redirect('portal:announcements')

    # Get user's events for the form
    user_events = Event.objects.filter(organizer=request.user)
    context = {
        'announcement': announcement,
        'user_events': user_events,
    }
    return render(request, 'portal/announcements/announcement_form.html', context)


@login_required(login_url="/accounts/login/")
def announcement_delete(request, pk):
    """Delete an announcement"""
    from src.api.models import Announcement
    announcement = get_object_or_404(Announcement, pk=pk, author=request.user)

    if request.method == 'POST':
        announcement.delete()
        messages.success(request, 'Announcement deleted successfully!')
        return redirect('portal:announcements')

    context = {'announcement': announcement}
    return render(request, 'portal/announcements/announcement_confirm_delete.html', context)


@login_required(login_url="/accounts/login/")
def entry_pass_view(request, event_pk, registration_pk):
    """Display entry pass when QR code is scanned"""
    event = get_object_or_404(Event, pk=event_pk)
    registration = get_object_or_404(Registration, pk=registration_pk, event=event, status='confirmed')

    # Generate entry pass page that will trigger print dialog
    context = {
        'event': event,
        'registration': registration,
        'attendee': registration.user,
    }
    return render(request, 'portal/events/entry_pass.html', context)

# ===============================
# REGISTRATION TYPE API ENDPOINTS
# ===============================

@login_required(login_url="/accounts/login/")
def registration_type_detail(request, pk):
    """API endpoint to get, update, or delete a single registration type"""
    from src.api.models import EventRegistrationType

    try:
        reg_type = EventRegistrationType.objects.get(pk=pk)

        # Check permission - only event organizer can access
        if reg_type.event.organizer != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)

        if request.method == 'GET':
            # Get registration type details
            data = {
                'id': reg_type.id,
                'name': reg_type.name,
                'description': reg_type.description,
                'is_paid': reg_type.is_paid,
                'amount': float(reg_type.amount),
                'payment_methods': reg_type.payment_methods,
                'is_active': reg_type.is_active,
                'order': reg_type.order,
            }
            return JsonResponse(data)

        elif request.method == 'PUT':
            # Update registration type
            try:
                data = json.loads(request.body)

                # Update fields
                reg_type.name = data.get('name', reg_type.name)
                reg_type.description = data.get('description', reg_type.description)
                reg_type.is_paid = data.get('is_paid', reg_type.is_paid)
                reg_type.amount = data.get('amount', reg_type.amount)
                reg_type.payment_methods = data.get('payment_methods', reg_type.payment_methods)
                reg_type.is_active = data.get('is_active', reg_type.is_active)
                reg_type.order = data.get('order', reg_type.order)

                reg_type.save()

                return JsonResponse({
                    'success': True,
                    'message': f"Registration type '{reg_type.name}' updated successfully!"
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)

        elif request.method == 'DELETE':
            # Delete registration type
            try:
                name = reg_type.name
                reg_type.delete()

                return JsonResponse({
                    'success': True,
                    'message': f"Registration type '{name}' deleted successfully!"
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)

        else:
            return JsonResponse({'error': 'Method not allowed'}, status=405)

    except EventRegistrationType.DoesNotExist:
        return JsonResponse({'error': 'Registration type not found'}, status=404)


@login_required(login_url="/accounts/login/")
def registration_type_create(request):
    """Create a new registration type"""
    from src.api.models import EventRegistrationType

    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('portal:dashboard')

    try:
        # Get event and check permission
        event_id = request.POST.get('event')
        event = get_object_or_404(Event, pk=event_id)

        if event.organizer != request.user:
            messages.error(request, 'Permission denied.')
            return redirect('portal:dashboard')

        # Get payment methods from checkboxes
        payment_methods = request.POST.getlist('payment_methods')

        # Handle is_paid checkbox
        is_paid = request.POST.get('is_paid') == 'on'

        # Handle is_active checkbox
        is_active = request.POST.get('is_active', 'on') == 'on'

        # Create registration type
        reg_type = EventRegistrationType.objects.create(
            event=event,
            name=request.POST.get('name'),
            description=request.POST.get('description', ''),
            is_paid=is_paid,
            amount=float(request.POST.get('amount', 0)) if is_paid else 0,
            payment_methods=payment_methods if is_paid else [],
            is_active=is_active,
            order=int(request.POST.get('order', 1)),
        )

        messages.success(request, f"Registration type '{reg_type.name}' created successfully!")
        return redirect(reverse('portal:event_detail', kwargs={'pk': event.pk}) + '#tab-settings')

    except Exception as e:
        messages.error(request, f'Error creating registration type: {str(e)}')
        return redirect('portal:dashboard')


@login_required(login_url="/accounts/login/")
def registration_type_edit(request, event_pk, reg_type_pk):
    """Edit an existing registration type"""
    from src.api.models import EventRegistrationType

    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    reg_type = get_object_or_404(EventRegistrationType, pk=reg_type_pk, event=event)

    if request.method == 'POST':
        try:
            # Get payment methods from checkboxes
            payment_methods = request.POST.getlist('payment_methods')

            # Handle is_paid checkbox
            is_paid = request.POST.get('is_paid') == 'on'

            # Handle is_active checkbox
            is_active = request.POST.get('is_active', 'on') == 'on'

            # Update registration type
            reg_type.name = request.POST.get('name')
            reg_type.description = request.POST.get('description', '')
            reg_type.is_paid = is_paid
            reg_type.amount = float(request.POST.get('amount', 0)) if is_paid else 0
            reg_type.payment_methods = payment_methods if is_paid else []
            reg_type.is_active = is_active
            reg_type.order = int(request.POST.get('order', 1))
            reg_type.save()

            messages.success(request, f"Registration type '{reg_type.name}' updated successfully!")
            return redirect(reverse('portal:event_detail', kwargs={'pk': event.pk}) + '#tab-settings')

        except Exception as e:
            messages.error(request, f'Error updating registration type: {str(e)}')
            return redirect('portal:event_detail', pk=event.pk)

    return redirect('portal:event_detail', pk=event.pk)


@login_required(login_url="/accounts/login/")
def registration_type_delete(request, event_pk, reg_type_pk):
    """Delete a registration type"""
    from src.api.models import EventRegistrationType

    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    reg_type = get_object_or_404(EventRegistrationType, pk=reg_type_pk, event=event)

    if request.method == 'POST':
        try:
            name = reg_type.name
            reg_type.delete()
            messages.success(request, f"Registration type '{name}' deleted successfully!")
            return redirect(reverse('portal:event_detail', kwargs={'pk': event.pk}) + '#tab-settings')

        except Exception as e:
            messages.error(request, f'Error deleting registration type: {str(e)}')
            return redirect('portal:event_detail', pk=event.pk)

    return redirect('portal:event_detail', pk=event.pk)


# ===============================
# BANK PAYMENT MANAGEMENT VIEWS
# ===============================

@login_required(login_url="/accounts/login/")
def update_bank_details(request, pk):
    """Update bank details for an event"""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if request.method == 'POST':
        bank_details = request.POST.get('bank_details', '')
        event.bank_details = bank_details
        event.save()

        messages.success(request, 'Bank details updated successfully!')
        return redirect(reverse('portal:event_detail', kwargs={'pk': event.pk}) + '#tab-settings')

    return redirect('portal:event_detail', pk=event.pk)


@login_required(login_url="/accounts/login/")
def approve_bank_receipt(request, event_pk, receipt_pk):
    """Approve a bank payment receipt"""
    from src.api.models import BankPaymentReceipt

    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    receipt = get_object_or_404(BankPaymentReceipt, pk=receipt_pk, event=event)

    if request.method == 'POST':
        receipt.approve(request.user)

        return JsonResponse({
            'success': True,
            'message': f'Receipt approved! Registration for {receipt.user.get_full_name()} is now confirmed.'
        })

    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required(login_url="/accounts/login/")
def reject_bank_receipt(request, event_pk, receipt_pk):
    """Reject a bank payment receipt"""
    from src.api.models import BankPaymentReceipt

    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    receipt = get_object_or_404(BankPaymentReceipt, pk=receipt_pk, event=event)

    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')

        if not rejection_reason:
            messages.error(request, 'Please provide a rejection reason.')
            return redirect(reverse('portal:event_detail', kwargs={'pk': event.pk}) + '#tab-settings')

        receipt.reject(request.user, rejection_reason)

        messages.success(request, f'Receipt rejected. User has been notified.')
        return redirect(reverse('portal:event_detail', kwargs={'pk': event.pk}) + '#tab-settings')

    return redirect('portal:event_detail', pk=event.pk)


@login_required(login_url="/accounts/login/")
def delete_bank_receipt(request, event_pk, receipt_pk):
    """Delete a bank payment receipt"""
    from src.api.models import BankPaymentReceipt

    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    receipt = get_object_or_404(BankPaymentReceipt, pk=receipt_pk, event=event)

    if request.method == 'POST':
        receipt.delete()

        return JsonResponse({
            'success': True,
            'message': 'Receipt deleted successfully.'
        })

    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required(login_url="/accounts/login/")
def registration_logs(request, pk):
    """View registration logs for an event with pagination"""
    from src.api.models import RegistrationLog
    from django.core.paginator import Paginator

    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    # Get all logs for this event, ordered by latest first
    logs = RegistrationLog.objects.filter(event=event).select_related(
        'user', 'registration', 'registration_type'
    ).order_by('-timestamp')

    # Pagination - 50 logs per page
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'event': event,
        'logs': page_obj,
        'page_obj': page_obj,
        'total_logs': logs.count(),
    }

    return render(request, 'portal/events/registration_logs.html', context)
