from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Sum
from .models import (
    Event, Agenda, Registration, Speaker, Session,
    Exhibitor, ExhibitionArea,
    SessionBookmark, Notification, Sponsor, SupportingMaterial, Announcement,
    AppContent, FAQ, ContactInfo, QuickAction
)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'status_badge',
        'date',
        'end_date',
        'location',
        'organizer',
        'attendee_count',
        'max_attendees',
        'signup_without_qr',
        'created_at'
    ]
    list_filter = [
        'status',
        'allow_signup_without_qr',
        'date',
        'created_at',
        'published_at'
    ]
    search_fields = [
        'title',
        'description',
        'location',
        'venue_details',
        'organizer__username',
        'organizer__email'
    ]
    date_hierarchy = 'date'
    ordering = ['-date']
    readonly_fields = ['published_at', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'organizer')
        }),
        ('Date & Location', {
            'fields': ('date', 'end_date', 'location', 'venue_details')
        }),
        ('Capacity & Status', {
            'fields': ('max_attendees', 'status', 'published_at')
        }),
        ('Registration Settings', {
            'fields': ('allow_signup_without_qr',),
            'description': 'Configure how users can register for this event'
        }),
        ('Media', {
            'fields': ('image',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['publish_events', 'cancel_events', 'mark_as_completed']

    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'published': 'green',
            'cancelled': 'red',
            'completed': 'blue'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def attendee_count(self, obj):
        count = obj.registrations.filter(status='confirmed').count()
        return f"{count}/{obj.max_attendees}"
    attendee_count.short_description = 'Attendees'

    def signup_without_qr(self, obj):
        if obj.allow_signup_without_qr:
            return format_html('<span style="color: green;">✓ Yes</span>')
        return format_html('<span style="color: red;">✗ No</span>')
    signup_without_qr.short_description = 'Signup w/o QR'

    def publish_events(self, request, queryset):
        published_count = 0
        for event in queryset:
            if event.status == 'draft':
                event.publish()
                published_count += 1
        self.message_user(request, f"{published_count} event(s) published successfully.")
    publish_events.short_description = "Publish selected events"

    def cancel_events(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f"{updated} event(s) cancelled.")
    cancel_events.short_description = "Cancel selected events"

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f"{updated} event(s) marked as completed.")
    mark_as_completed.short_description = "Mark as completed"


@admin.register(Agenda)
class AgendaAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'event_link',
        'date',
        'order',
        'session_count',
        'created_at'
    ]
    list_filter = [
        'date',
        'event',
        'created_at'
    ]
    search_fields = [
        'title',
        'description',
        'event__title'
    ]
    ordering = ['event', 'order', 'date']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('event', 'title', 'description')
        }),
        ('Schedule', {
            'fields': ('date', 'order')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def event_link(self, obj):
        url = reverse('admin:api_event_change', args=[obj.event.id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title[:30])
    event_link.short_description = 'Event'

    def session_count(self, obj):
        return obj.sessions.count()
    session_count.short_description = 'Sessions'


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'registration_id',
        'user_email',
        'event_link',
        'status_badge',
        'registered_at'
    ]
    list_filter = [
        'status',
        'registered_at',
        'event',
        'event__status'
    ]
    search_fields = [
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'event__title'
    ]
    date_hierarchy = 'registered_at'
    ordering = ['-registered_at']
    readonly_fields = ['registered_at']

    def registration_id(self, obj):
        return f"REG-{obj.id:05d}"
    registration_id.short_description = 'Registration ID'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def event_link(self, obj):
        url = reverse('admin:api_event_change', args=[obj.event.id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title)
    event_link.short_description = 'Event'

    def status_badge(self, obj):
        colors = {
            'confirmed': 'green',
            'pending': 'orange',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    actions = ['confirm_registrations', 'cancel_registrations']

    def confirm_registrations(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f"{updated} registration(s) confirmed.")
    confirm_registrations.short_description = "Confirm selected registrations"

    def cancel_registrations(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f"{updated} registration(s) cancelled.")
    cancel_registrations.short_description = "Cancel selected registrations"


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'title',
        'company',
        'email',
        'has_photo',
        'social_links',
        'session_count'
    ]
    list_filter = [
        'created_at',
        ('photo', admin.EmptyFieldListFilter),
    ]
    search_fields = [
        'name',
        'title',
        'company',
        'email',
        'bio'
    ]
    ordering = ['name']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'email', 'photo')
        }),
        ('Professional Details', {
            'fields': ('title', 'company', 'bio')
        }),
        ('Social Media', {
            'fields': ('linkedin_url', 'twitter_url'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def has_photo(self, obj):
        return "✓" if obj.photo else "✗"
    has_photo.short_description = 'Photo'

    def social_links(self, obj):
        links = []
        if obj.linkedin_url:
            links.append(format_html('<a href="{}" target="_blank">LinkedIn</a>', obj.linkedin_url))
        if obj.twitter_url:
            links.append(format_html('<a href="{}" target="_blank">Twitter</a>', obj.twitter_url))
        return format_html(' | '.join(links)) if links else '-'
    social_links.short_description = 'Social'

    def session_count(self, obj):
        return obj.sessions.count()
    session_count.short_description = 'Sessions'


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'agenda_link',
        'event_link',
        'session_type_badge',
        'start_time',
        'duration',
        'location',
        'speaker_list',
        'attendee_limit'
    ]
    list_filter = [
        'session_type',
        'agenda',
        'start_time',
        'agenda__event__status'
    ]
    search_fields = [
        'title',
        'description',
        'location',
        'agenda__title',
        'agenda__event__title',
        'speakers__name'
    ]
    filter_horizontal = ['speakers']
    # date_hierarchy = 'start_time'  # Removed since start_time is now TimeField
    ordering = ['agenda__event', 'agenda__order', 'start_time']
    readonly_fields = ['duration_display']

    fieldsets = (
        ('Basic Information', {
            'fields': ('agenda', 'title', 'description', 'session_type')
        }),
        ('Schedule & Location', {
            'fields': ('start_time', 'end_time', 'duration_display', 'location')
        }),
        ('Speakers & Capacity', {
            'fields': ('speakers', 'max_attendees')
        }),
        ('Materials', {
            'fields': ('materials_url',),
            'classes': ('collapse',)
        })
    )

    def agenda_link(self, obj):
        url = reverse('admin:api_agenda_change', args=[obj.agenda.id])
        return format_html('<a href="{}">{}</a>', url, obj.agenda.title[:30])
    agenda_link.short_description = 'Agenda'

    def event_link(self, obj):
        url = reverse('admin:api_event_change', args=[obj.agenda.event.id])
        return format_html('<a href="{}">{}</a>', url, obj.agenda.event.title[:30])
    event_link.short_description = 'Event'

    def session_type_badge(self, obj):
        colors = {
            'keynote': 'purple',
            'workshop': 'blue',
            'panel': 'green',
            'networking': 'orange',
            'break': 'gray',
            'presentation': 'teal'
        }
        color = colors.get(obj.session_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_session_type_display()
        )
    session_type_badge.short_description = 'Type'

    def duration(self, obj):
        if obj.start_time and obj.end_time:
            delta = obj.end_time - obj.start_time
            hours = int(delta.total_seconds() // 3600)
            minutes = int((delta.total_seconds() % 3600) // 60)
            if hours:
                return f"{hours}h {minutes}m" if minutes else f"{hours}h"
            return f"{minutes}m"
        return '-'
    duration.short_description = 'Duration'

    def duration_display(self, obj):
        return self.duration(obj)
    duration_display.short_description = 'Duration'

    def speaker_list(self, obj):
        speakers = obj.speakers.all()[:3]
        names = [s.name for s in speakers]
        if obj.speakers.count() > 3:
            names.append(f"+{obj.speakers.count() - 3} more")
        return ', '.join(names) if names else '-'
    speaker_list.short_description = 'Speakers'

    def attendee_limit(self, obj):
        return obj.max_attendees if obj.max_attendees else 'Unlimited'
    attendee_limit.short_description = 'Max Attendees'



@admin.register(Exhibitor)
class ExhibitorAdmin(admin.ModelAdmin):
    list_display = [
        'company_name',
        'event_link',
        'booth_display',
        'contact_display',
        'has_logo',
        'approval_status',
        'created_at'
    ]
    list_filter = [
        'approved',
        'event',
        'created_at',
        ('logo', admin.EmptyFieldListFilter)
    ]
    search_fields = [
        'company_name',
        'contact_person',
        'email',
        'booth_number',
        'description'
    ]
    ordering = ['event', 'booth_number']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'description', 'logo', 'website')
        }),
        ('Contact Details', {
            'fields': ('contact_person', 'email', 'phone')
        }),
        ('Booth Information', {
            'fields': ('event', 'booth_number', 'booth_size', 'special_requirements')
        }),
        ('Approval', {
            'fields': ('approved', 'created_at')
        })
    )

    def event_link(self, obj):
        url = reverse('admin:api_event_change', args=[obj.event.id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title[:30])
    event_link.short_description = 'Event'

    def booth_display(self, obj):
        return f"#{obj.booth_number} ({obj.booth_size})"
    booth_display.short_description = 'Booth'

    def contact_display(self, obj):
        return format_html(
            '{}<br><small>{}</small>',
            obj.contact_person,
            obj.email
        )
    contact_display.short_description = 'Contact'

    def has_logo(self, obj):
        return "✓" if obj.logo else "✗"
    has_logo.short_description = 'Logo'

    def approval_status(self, obj):
        if obj.approved:
            return format_html('<span style="color: green;">✓ Approved</span>')
        return format_html('<span style="color: orange;">⏳ Pending</span>')
    approval_status.short_description = 'Status'

    actions = ['approve_exhibitors', 'reject_exhibitors']

    def approve_exhibitors(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(request, f"{updated} exhibitor(s) approved.")
    approve_exhibitors.short_description = "Approve selected exhibitors"

    def reject_exhibitors(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(request, f"{updated} exhibitor(s) rejected.")
    reject_exhibitors.short_description = "Reject selected exhibitors"


@admin.register(ExhibitionArea)
class ExhibitionAreaAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'event_link',
        'total_booths',
        'price_display',
        'has_floor_plan',
        'booth_occupancy',
        'potential_revenue'
    ]
    list_filter = [
        'event',
        ('floor_plan', admin.EmptyFieldListFilter),
        'event__status'
    ]
    search_fields = [
        'name',
        'description',
        'event__title'
    ]
    ordering = ['event', 'name']

    fieldsets = (
        ('Basic Information', {
            'fields': ('event', 'name', 'description')
        }),
        ('Booth Configuration', {
            'fields': ('total_booths', 'booth_price')
        }),
        ('Floor Plan', {
            'fields': ('floor_plan',),
            'classes': ('collapse',)
        })
    )

    def event_link(self, obj):
        url = reverse('admin:api_event_change', args=[obj.event.id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title[:30])
    event_link.short_description = 'Event'

    def price_display(self, obj):
        return f"₨{obj.booth_price:,.2f}"
    price_display.short_description = 'Booth Price'
    price_display.admin_order_field = 'booth_price'

    def has_floor_plan(self, obj):
        return "✓" if obj.floor_plan else "✗"
    has_floor_plan.short_description = 'Floor Plan'

    def booth_occupancy(self, obj):
        occupied = obj.event.exhibitors.filter(approved=True).count()
        percentage = (occupied / obj.total_booths * 100) if obj.total_booths > 0 else 0
        color = 'green' if percentage < 75 else 'orange' if percentage < 95 else 'red'
        return format_html(
            '<span style="color: {};">{}/{} ({:.0f}%)</span>',
            color, occupied, obj.total_booths, percentage
        )
    booth_occupancy.short_description = 'Occupancy'

    def potential_revenue(self, obj):
        revenue = obj.total_booths * obj.booth_price
        return f"₨{revenue:,.2f}"
    potential_revenue.short_description = 'Potential Revenue'


@admin.register(SessionBookmark)
class SessionBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'session', 'event_name', 'created_at']
    list_filter = ['created_at', 'session__agenda__event']
    search_fields = ['user__username', 'user__email', 'session__title']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def event_name(self, obj):
        return obj.session.agenda.event.title
    event_name.short_description = 'Event'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'user',
        'notification_type',
        'event_link',
        'is_read',
        'created_at',
        'scheduled_for'
    ]
    list_filter = [
        'notification_type',
        'is_read',
        'created_at',
        'scheduled_for'
    ]
    search_fields = [
        'title',
        'message',
        'user__username',
        'user__email',
        'event__title'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = ['created_at']

    def event_link(self, obj):
        if obj.event:
            url = reverse('admin:api_event_change', args=[obj.event.id])
            return format_html('<a href="{}">{}</a>', url, obj.event.title[:30])
        return '-'
    event_link.short_description = 'Event'

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} notification(s) marked as read.")
    mark_as_read.short_description = "Mark as read"

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} notification(s) marked as unread.")
    mark_as_unread.short_description = "Mark as unread"



@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'has_logo',
        'website_link',
        'contact_info',
        'event_count',
        'created_at'
    ]
    list_filter = [
        'created_at',
        'updated_at',
        ('logo', admin.EmptyFieldListFilter)
    ]
    search_fields = [
        'title',
        'description',
        'email',
        'phone',
        'website'
    ]
    # filter_horizontal = ['events']  # Events is managed from Event admin, not here
    ordering = ['title']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'logo')
        }),
        ('Contact Details', {
            'fields': ('website', 'email', 'phone')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def has_logo(self, obj):
        return "✓" if obj.logo else "✗"
    has_logo.short_description = 'Logo'

    def website_link(self, obj):
        if obj.website:
            return format_html('<a href="{}" target="_blank">Visit</a>', obj.website)
        return '-'
    website_link.short_description = 'Website'

    def contact_info(self, obj):
        contact = []
        if obj.email:
            contact.append(obj.email)
        if obj.phone:
            contact.append(obj.phone)
        return ' | '.join(contact) if contact else '-'
    contact_info.short_description = 'Contact'

    def event_count(self, obj):
        count = obj.events.count()
        if count > 0:
            return format_html(
                '<span style="color: green;">{} event{}</span>',
                count, 's' if count != 1 else ''
            )
        return format_html('<span style="color: gray;">No events</span>')
    event_count.short_description = 'Events'


@admin.register(SupportingMaterial)
class SupportingMaterialAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'event_link',
        'material_type_badge',
        'file_info',
        'is_public',
        'uploaded_by',
        'created_at'
    ]
    list_filter = [
        'material_type',
        'is_public',
        'created_at',
        'event',
        'uploaded_by'
    ]
    search_fields = [
        'title',
        'description',
        'event__title',
        'uploaded_by__username'
    ]
    ordering = ['event', 'order', '-created_at']
    readonly_fields = ['file_size', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('event', 'title', 'description', 'material_type')
        }),
        ('File & Visibility', {
            'fields': ('file', 'file_size', 'is_public', 'order')
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def event_link(self, obj):
        url = reverse('admin:api_event_change', args=[obj.event.id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title[:40])
    event_link.short_description = 'Event'

    def material_type_badge(self, obj):
        colors = {
            'slides': 'blue',
            'poster': 'green',
            'demo': 'orange',
            'handout': 'purple',
            'video': 'red',
            'document': 'gray',
            'other': 'dark'
        }
        color = colors.get(obj.material_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_material_type_display()
        )
    material_type_badge.short_description = 'Type'

    def file_info(self, obj):
        if obj.file:
            extension = obj.get_file_extension()
            size = obj.get_file_size_display()
            return format_html(
                '<span class="badge bg-secondary me-1">{}</span> <span class="text-muted">{}</span>',
                extension, size
            )
        return '-'
    file_info.short_description = 'File Info'


@admin.register(QuickAction)
class QuickActionAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'event_link',
        'icon_display',
        'materials_count',
        'order',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'is_active',
        'icon',
        'created_at',
        'event'
    ]
    search_fields = [
        'title',
        'info_line',
        'event__title'
    ]
    ordering = ['event', 'order', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ('supporting_materials',)  # This creates the nice multi-select widget

    fieldsets = (
        ('Basic Information', {
            'fields': ('event', 'title', 'icon', 'info_line')
        }),
        ('Supporting Materials', {
            'fields': ('supporting_materials',),
            'description': 'Select multiple supporting materials for this quick action. Hold Ctrl/Cmd to select multiple items.'
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def event_link(self, obj):
        url = reverse('admin:api_event_change', args=[obj.event.id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title[:40])
    event_link.short_description = 'Event'

    def icon_display(self, obj):
        icon_class = obj.get_icon_class()
        return format_html(
            '<i class="{}" style="font-size: 18px; color: #007bff;"></i> <span style="margin-left: 5px;">{}</span>',
            icon_class, obj.get_icon_display()
        )
    icon_display.short_description = 'Icon'

    def materials_count(self, obj):
        count = obj.supporting_materials.count()
        if count > 0:
            return format_html(
                '<span class="badge bg-success">{} material{}</span>',
                count, 's' if count != 1 else ''
            )
        return format_html('<span class="badge bg-secondary">No materials</span>')
    materials_count.short_description = 'Materials'

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Customize the queryset for supporting_materials field to show only materials from the same event"""
        if db_field.name == "supporting_materials":
            # If we're editing an existing quick action, filter materials by its event
            if request.resolver_match.kwargs.get('object_id'):
                try:
                    quick_action = QuickAction.objects.get(pk=request.resolver_match.kwargs['object_id'])
                    kwargs["queryset"] = SupportingMaterial.objects.filter(event=quick_action.event, is_public=True)
                except QuickAction.DoesNotExist:
                    pass
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',)
        }

    def is_public(self, obj):
        if obj.is_public:
            return format_html('<span style="color: green;">✓ Public</span>')
        return format_html('<span style="color: orange;">🔒 Private</span>')
    is_public.short_description = 'Visibility'


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'type',
        'priority_badge',
        'event',
        'author',
        'status_badge',
        'recipients_count',
        'created_at'
    ]
    list_filter = [
        'type',
        'priority',
        'is_active',
        'author',
        'event',
        'created_at'
    ]
    search_fields = [
        'title',
        'content',
        'author__username',
        'event__title'
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (None, {
            'fields': ('title', 'content', 'type', 'event', 'priority', 'author', 'is_active')
        }),
        ('Scheduling', {
            'fields': ('publish_date', 'expire_date'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def priority_badge(self, obj):
        colors = {
            'low': '#6c757d',
            'medium': '#17a2b8',
            'high': '#ffc107',
            'urgent': '#dc3545'
        }
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'

    def status_badge(self, obj):
        if obj.is_active:
            if obj.is_expired():
                return format_html('<span style="color: orange;">⏰ Expired</span>')
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    status_badge.short_description = 'Status'

    def recipients_count(self, obj):
        count = obj.get_recipients_count()
        return format_html('<strong>{}</strong> users', count)
    recipients_count.short_description = 'Recipients'


@admin.register(AppContent)
class AppContentAdmin(admin.ModelAdmin):
    list_display = [
        'content_type',
        'title',
        'version',
        'status_badge',
        'last_updated',
        'created_at'
    ]
    list_filter = [
        'content_type',
        'is_active',
        'last_updated',
        'created_at'
    ]
    search_fields = [
        'title',
        'content'
    ]
    ordering = ['content_type']
    readonly_fields = ['created_at', 'last_updated']

    fieldsets = (
        ('Basic Information', {
            'fields': ('content_type', 'title', 'version', 'is_active')
        }),
        ('Content', {
            'fields': ('content',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'last_updated'),
            'classes': ('collapse',)
        })
    )

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    status_badge.short_description = 'Status'


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = [
        'question',
        'category_badge',
        'order',
        'status_badge',
        'updated_at'
    ]
    list_filter = [
        'category',
        'is_active',
        'created_at',
        'updated_at'
    ]
    search_fields = [
        'question',
        'answer'
    ]
    ordering = ['category', 'order', 'question']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('question', 'answer', 'category', 'order', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def category_badge(self, obj):
        colors = {
            'general': '#6c757d',
            'events': '#007bff',
            'registration': '#28a745',
            'account': '#ffc107',
            'technical': '#dc3545'
        }
        color = colors.get(obj.category, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_category_display()
        )
    category_badge.short_description = 'Category'

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    status_badge.short_description = 'Status'


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = [
        'label',
        'contact_type_badge',
        'value',
        'order',
        'status_badge',
        'created_at'
    ]
    list_filter = [
        'contact_type',
        'is_active',
        'created_at'
    ]
    search_fields = [
        'label',
        'value'
    ]
    ordering = ['contact_type', 'order']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Contact Information', {
            'fields': ('contact_type', 'label', 'value', 'order', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def contact_type_badge(self, obj):
        colors = {
            'email': '#007bff',
            'phone': '#28a745',
            'address': '#ffc107',
            'social_media': '#e83e8c'
        }
        color = colors.get(obj.contact_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_contact_type_display()
        )
    contact_type_badge.short_description = 'Type'

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    status_badge.short_description = 'Status'
