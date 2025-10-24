from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class EventRegistrationType(models.Model):
    """Registration types specific to each event"""
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='registration_types')
    name = models.CharField(max_length=100, help_text='e.g., Student, Professional, Academic, Industry')
    description = models.TextField(blank=True, help_text='Brief description of this registration type')

    # Payment fields
    is_paid = models.BooleanField(default=False, help_text='Does this registration type require payment?')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Registration fee for this type in PKR')
    payment_methods = models.JSONField(default=list, blank=True, help_text='Allowed payment methods: ["mwallet", "card"]')

    # Status and ordering
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['event', 'order', 'name']
        unique_together = ['event', 'name']

    def __str__(self):
        return f"{self.event.title} - {self.name}"


class Event(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200)
    venue_details = models.TextField(blank=True)
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    max_attendees = models.IntegerField(default=100)
    image = models.ImageField(upload_to='events/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    published_at = models.DateTimeField(null=True, blank=True)
    allow_signup_without_qr = models.BooleanField(default=False, help_text='Allow users to sign up without scanning QR code')
    sponsors = models.ManyToManyField('Sponsor', blank=True, related_name='events')

    # Payment fields
    is_paid_event = models.BooleanField(default=False, help_text='Does this event require payment?')
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Registration fee in PKR')
    payment_methods = models.JSONField(default=list, blank=True, help_text='Allowed payment methods: ["mwallet", "card"]')
    bank_details = models.TextField(blank=True, help_text='Bank details for manual bank transfers')

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return self.title

    def publish(self):
        self.status = 'published'
        self.published_at = timezone.now()
        self.save()

    def is_published(self):
        return self.status == 'published'


class Agenda(models.Model):
    """An agenda represents a day or section of an event (e.g., Day 1, Day 2, Workshops, Keynotes)"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='agendas')
    title = models.CharField(max_length=200)  # e.g., "Day 1 - Workshops", "Day 2 - Keynotes"
    description = models.TextField(blank=True)
    date = models.DateField()  # The specific date for this agenda
    order = models.PositiveIntegerField(default=1)  # For ordering multiple agendas
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'date']

    def __str__(self):
        return f"{self.title} - {self.event.title}"

    @property
    def day_number(self):
        """Calculate the day number based on date difference from event start date"""
        if self.date and self.event.date:
            event_start_date = self.event.date.date()
            days_diff = (self.date - event_start_date).days
            return days_diff + 1
        return self.order


class AgendaTopic(models.Model):
    """Topics/tracks for agendas - One agenda can have many topics"""
    agenda = models.ForeignKey(Agenda, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=100)  # e.g., "AI & Technology", "Business Innovation"
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')  # Hex color for UI
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']
        unique_together = ['agenda', 'name']  # Prevent duplicate topic names per agenda

    def __str__(self):
        return f"{self.name} - {self.agenda.title}"


class AgendaCoordinator(models.Model):
    """Coordinators for agendas - One agenda can have many coordinators"""
    agenda = models.ForeignKey(Agenda, on_delete=models.CASCADE, related_name='coordinators')
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=100, blank=True)  # e.g., "Lead Coordinator", "Technical Support"
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ['agenda', 'email']  # Prevent duplicate coordinators per agenda

    def __str__(self):
        return f"{self.name} - {self.agenda.title}"


class Registration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='registrations')
    registered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('confirmed', 'Confirmed'),
            ('pending', 'Pending'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'

    )

    # Registration Details - stored at registration time
    registration_type = models.ForeignKey('EventRegistrationType', on_delete=models.SET_NULL, null=True, blank=True, related_name='registrations')
    designation = models.CharField(max_length=200, blank=True, help_text='Job title or designation')
    affiliations = models.CharField(max_length=300, blank=True, help_text='Organization or institution')
    address = models.TextField(blank=True, help_text='Mailing address')
    country = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    selected_workshops = models.ManyToManyField('Session', blank=True, related_name='workshop_registrations', limit_choices_to={'session_type': 'workshop'})

    # Payment fields
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('unpaid', 'Unpaid'),
            ('pending', 'Payment Pending'),
            ('paid', 'Paid'),
            ('refunded', 'Refunded'),
        ],
        default='unpaid'
    )
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['event', 'user']
        ordering = ['-registered_at']

    def __str__(self):
        return f"{self.user.username} - {self.event.title}"

    @property
    def registration_id(self):
        """Return formatted registration ID"""
        return f"REG-{self.id:05d}"


class Speaker(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    bio = models.TextField()
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True)
    photo = models.ImageField(upload_to='speakers/', null=True, blank=True)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Session(models.Model):
    SESSION_TYPES = [
        ('keynote', 'Keynote'),
        ('workshop', 'Workshop'),
        ('panel', 'Panel Discussion'),
        ('networking', 'Networking'),
        ('break', 'Break'),
        ('presentation', 'Presentation'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='sessions_old', null=True, blank=True)
    agenda = models.ForeignKey(Agenda, on_delete=models.CASCADE, related_name='sessions', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='presentation')
    speakers = models.ManyToManyField(Speaker, related_name='sessions', blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=200, blank=True)
    max_attendees = models.IntegerField(null=True, blank=True)
    materials_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=1)

    # Session Registration Fields
    slots_available = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of available slots. Leave empty for unlimited."
    )
    allow_registration = models.BooleanField(
        default=False,
        help_text="Allow attendees to register for this session"
    )

    # Payment fields
    is_paid_session = models.BooleanField(default=False, help_text='Does this session require payment?')
    session_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Session registration fee in PKR')
    payment_methods = models.JSONField(default=list, blank=True, help_text='Allowed payment methods: ["mwallet", "card"]')

    class Meta:
        ordering = ['order', 'start_time']

    def __str__(self):
        if self.agenda:
            return f"{self.title} - {self.agenda.title}"
        elif self.event:
            return f"{self.title} - {self.event.title}"
        return self.title

    def get_event(self):
        """Get the event through the agenda or direct relationship"""
        if self.agenda:
            return self.agenda.event
        elif hasattr(self, 'event') and self.event:
            return self.event
        return None



class LiveStreamURL(models.Model):
    """Live stream URLs for sessions"""
    PLATFORM_CHOICES = [
        ('youtube', 'YouTube'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('tiktok', 'TikTok'),
        ('twitter', 'Twitter (X)'),
        ('zoom', 'Zoom'),
        ('other', 'Other'),
    ]

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='live_stream_urls'
    )
    stream_url = models.URLField(max_length=500, help_text='Live stream URL')
    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
        default='other',
        help_text='Streaming platform'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['platform', 'created_at']
        verbose_name = 'Live Stream URL'
        verbose_name_plural = 'Live Stream URLs'

    def __str__(self):
        return f"{self.get_platform_display()} - {self.session.title}"


class Exhibitor(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='exhibitors')
    company_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    website = models.URLField(blank=True)
    description = models.TextField()
    logo = models.ImageField(upload_to='exhibitors/', null=True, blank=True)
    booth_number = models.CharField(max_length=50)
    booth_size = models.CharField(max_length=50)
    special_requirements = models.TextField(blank=True)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company_name} - Booth {self.booth_number}"


class ExhibitionArea(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='exhibition_areas')
    name = models.CharField(max_length=200)
    floor_plan = models.ImageField(upload_to='exhibition/floor_plans/', null=True, blank=True)
    total_booths = models.IntegerField()
    booth_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.event.title}"




# Conference Features Models
class CheckIn(models.Model):
    """Track attendee check-ins at events"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='checkins')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='checkins')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='checkins')
    checked_in_at = models.DateTimeField(auto_now_add=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performed_checkins'
    )
    check_in_method = models.CharField(
        max_length=20,
        choices=[
            ('qr_code', 'QR Code'),
            ('manual', 'Manual'),
            ('self', 'Self Check-in'),
        ],
        default='qr_code'
    )

    class Meta:
        ordering = ['-checked_in_at']
        # Prevent duplicate check-ins for the same registration
        unique_together = ['registration', 'event']

    def __str__(self):
        return f"{self.user.username} checked in at {self.event.title} on {self.checked_in_at}"


class SessionRegistration(models.Model):
    """Simple registration tracking for sessions"""
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='session_registrations')
    registered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('confirmed', 'Confirmed'),
            ('pending', 'Pending'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )

    # Payment fields
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('unpaid', 'Unpaid'),
            ('pending', 'Payment Pending'),
            ('paid', 'Paid'),
            ('refunded', 'Refunded'),
        ],
        default='unpaid'
    )
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-registered_at']
        unique_together = ['session', 'user']  # Prevent duplicate registrations

    def __str__(self):
        return f"{self.user.username} - {self.session.title}"

    def save(self, *args, **kwargs):
        # Check if slots are available before saving
        if self.session.slots_available is not None:
            current_registrations = SessionRegistration.objects.filter(
                session=self.session
            ).exclude(pk=self.pk).count()

            if current_registrations >= self.session.slots_available:
                raise ValueError("No slots available for this session")

        super().save(*args, **kwargs)


class SessionBookmark(models.Model):
    """Allow attendees to bookmark sessions"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookmarked_sessions')
    session = models.ForeignKey('Session', on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'session']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.session.title}"


class AgendaLike(models.Model):
    """Allow users to like agendas"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='liked_agendas')
    agenda = models.ForeignKey('Agenda', on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'agenda']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.agenda.title}"


class Notification(models.Model):
    """Notifications for users"""
    NOTIFICATION_TYPES = [
        ('session_reminder', 'Session Reminder'),
        ('event_update', 'Event Update'),
        ('registration', 'Registration Confirmation'),
        ('check_in', 'Check-in Confirmation'),
        ('announcement', 'Announcement'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    event = models.ForeignKey('Event', on_delete=models.CASCADE, null=True, blank=True)
    session = models.ForeignKey('Session', on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)  # For scheduled notifications

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"




class VenueMap(models.Model):
    """Store venue maps and floor plans for events"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='venue_maps')
    title = models.CharField(max_length=200)  # e.g., "Main Entrance Map", "Conference Hall Direction"
    description = models.TextField(blank=True, help_text="Optional description of what this map shows")
    image = models.ImageField(upload_to='venue_maps/', help_text="Upload the venue map image")
    order = models.PositiveIntegerField(default=1, help_text="Order of display")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Venue Map'
        verbose_name_plural = 'Venue Maps'

    def __str__(self):
        return f"{self.event.title} - {self.title}"


class Sponsor(models.Model):
    """Sponsor model for event sponsors"""
    title = models.CharField(max_length=200, help_text="Company/sponsor name")
    description = models.TextField(help_text="About the sponsor")
    logo = models.ImageField(upload_to='sponsors/', null=True, blank=True, help_text="Upload sponsor logo")
    website = models.URLField(blank=True, help_text="Sponsor website URL")
    email = models.EmailField(blank=True, help_text="Sponsor contact email")
    phone = models.CharField(max_length=20, blank=True, help_text="Sponsor contact phone")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Sponsor'
        verbose_name_plural = 'Sponsors'

    def __str__(self):
        return self.title


class QuickAction(models.Model):
    """Quick actions for events with supporting materials"""
    ICON_CHOICES = [
        ('download', 'Download'),
        ('view', 'View/Eye'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('image', 'Image'),
        ('presentation', 'Presentation'),
        ('link', 'Link'),
        ('info', 'Info'),
        ('calendar', 'Calendar'),
        ('map', 'Map'),
        ('qrcode', 'QR Code'),
        ('ticket', 'Ticket'),
        ('certificate', 'Certificate'),
        ('badge', 'Badge'),
        ('folder', 'Folder'),
        ('poster', 'Poster'),
        ('banner', 'Banner'),
        ('research_paper', 'Research Paper'),
    ]

    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='quick_actions')
    title = models.CharField(max_length=200, help_text="Quick action title")
    icon = models.CharField(max_length=50, choices=ICON_CHOICES, default='download', help_text="Icon for the quick action")
    info_line = models.CharField(max_length=500, blank=True, help_text="Brief description or info about this action")
    supporting_materials = models.ManyToManyField('SupportingMaterial', related_name='quick_actions', blank=True, help_text="Select supporting materials for this action")
    order = models.PositiveIntegerField(default=1, help_text="Display order")
    is_active = models.BooleanField(default=True, help_text="Is this action active?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Quick Action'
        verbose_name_plural = 'Quick Actions'

    def __str__(self):
        return f"{self.title} - {self.event.title}"

    def get_icon_class(self):
        """Get the CSS class for the icon"""
        icon_classes = {
            'download': 'fas fa-download',
            'view': 'fas fa-eye',
            'document': 'fas fa-file-alt',
            'video': 'fas fa-video',
            'image': 'fas fa-image',
            'presentation': 'fas fa-presentation',
            'link': 'fas fa-link',
            'info': 'fas fa-info-circle',
            'calendar': 'fas fa-calendar',
            'map': 'fas fa-map-marker-alt',
            'qrcode': 'fas fa-qrcode',
            'ticket': 'fas fa-ticket-alt',
            'certificate': 'fas fa-certificate',
            'badge': 'fas fa-id-badge',
            'folder': 'fas fa-folder',
            'poster': 'fas fa-image',
            'banner': 'fas fa-flag',
            'research_paper': 'fas fa-file-alt',
        }
        return icon_classes.get(self.icon, 'fas fa-file')


class SupportingMaterial(models.Model):
    """Supporting materials for events (slides, posters, demo info, etc.)"""
    MATERIAL_TYPES = [
        ('slides', 'Presentation Slides'),
        ('poster', 'Poster/Banner'),
        ('demo', 'Demo Information'),
        ('handout', 'Handout/Brochure'),
        ('video', 'Video Content'),
        ('document', 'Document'),
        ('other', 'Other'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='supporting_materials')
    title = models.CharField(max_length=200, help_text="Material title")
    description = models.TextField(blank=True, help_text="Description of the material")
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPES, default='document', help_text="Type of supporting material")
    file = models.FileField(upload_to='supporting_materials/', help_text="Upload the supporting material file")
    file_size = models.PositiveIntegerField(blank=True, null=True, help_text="File size in bytes")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_materials')
    is_public = models.BooleanField(default=True, help_text="Make this material publicly accessible")
    order = models.PositiveIntegerField(default=1, help_text="Display order")
    sessions = models.ManyToManyField('Session', related_name='supporting_materials', blank=True, help_text="Sessions this material is associated with")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Supporting Material'
        verbose_name_plural = 'Supporting Materials'

    def __str__(self):
        return f"{self.event.title} - {self.title}"

    def save(self, *args, **kwargs):
        # Calculate file size if not set
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except (ValueError, AttributeError):
                pass
        super().save(*args, **kwargs)

    def get_file_size_display(self):
        """Return human readable file size"""
        if not self.file_size:
            return 'Unknown'

        size = self.file_size
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def get_file_extension(self):
        """Return file extension"""
        if self.file:
            return self.file.name.split('.')[-1].upper() if '.' in self.file.name else 'FILE'
        return 'FILE'


class Announcement(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    TYPE_CHOICES = [
        ('general', 'General'),
        ('event_specific', 'Event Specific'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='general')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True, related_name='announcements')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='announcements')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    publish_date = models.DateTimeField(default=timezone.now)
    expire_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return self.title

    def is_expired(self):
        if self.expire_date:
            return timezone.now() > self.expire_date
        return False

    def get_priority_badge_class(self):
        priority_classes = {
            'low': 'bg-secondary',
            'medium': 'bg-info',
            'high': 'bg-warning',
            'urgent': 'bg-danger',
        }
        return priority_classes.get(self.priority, 'bg-secondary')

    def get_recipients_count(self):
        """Get count of users who will see this announcement"""
        if self.type == 'event_specific' and self.event:
            return Registration.objects.filter(event=self.event, status='confirmed').count()
        else:
            # General announcements are visible to all attendees of author's events
            user_events = Event.objects.filter(organizer=self.author)
            return Registration.objects.filter(
                event__in=user_events,
                status='confirmed'
            ).values('user').distinct().count()


class AppContent(models.Model):
    """Model for app content pages like Privacy Policy, Help & Support, About"""
    CONTENT_TYPES = [
        ('privacy_policy', 'Privacy & Security'),
        ('help_support', 'Help & Support'),
        ('about', 'About'),
        ('terms_conditions', 'Terms & Conditions'),
    ]

    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, unique=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    version = models.CharField(max_length=10, default='1.0')
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['content_type']
        verbose_name = 'App Content'
        verbose_name_plural = 'App Contents'

    def __str__(self):
        return f"{self.get_content_type_display()} - v{self.version}"


class FAQ(models.Model):
    """Frequently Asked Questions"""
    question = models.CharField(max_length=300)
    answer = models.TextField()
    category = models.CharField(max_length=50, choices=[
        ('general', 'General'),
        ('events', 'Events'),
        ('registration', 'Registration'),
        ('account', 'Account'),
        ('technical', 'Technical Support'),
    ], default='general')
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'order', 'question']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question


class ContactInfo(models.Model):
    """Contact information for support"""
    contact_type = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('address', 'Address'),
        ('social_media', 'Social Media'),
    ])
    label = models.CharField(max_length=100)  # e.g., "Support Email", "Main Office"
    value = models.CharField(max_length=300)  # The actual contact info
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['contact_type', 'order']
        verbose_name = 'Contact Info'
        verbose_name_plural = 'Contact Information'

    def __str__(self):
        return f"{self.label}: {self.value}"

class AppDownload(models.Model):
    """Model to store APK files for app download"""
    version = models.CharField(max_length=20, help_text="App version (e.g., 1.0.0)")
    apk_file = models.FileField(upload_to='apk/', help_text="Upload the APK file")
    release_notes = models.TextField(blank=True, help_text="What's new in this version")
    is_active = models.BooleanField(default=True, help_text="Only one version should be active at a time")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.CharField(max_length=50, blank=True, editable=False)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'App Download'
        verbose_name_plural = 'App Downloads'

    def __str__(self):
        return f"JIC App v{self.version}"

    def save(self, *args, **kwargs):
        # Calculate file size
        if self.apk_file:
            size_bytes = self.apk_file.size
            if size_bytes < 1024:
                self.file_size = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                self.file_size = f"{size_bytes / 1024:.2f} KB"
            else:
                self.file_size = f"{size_bytes / (1024 * 1024):.2f} MB"
        
        # If this is being set as active, deactivate all others
        if self.is_active:
            AppDownload.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)

        super().save(*args, **kwargs)


class BankPaymentReceipt(models.Model):
    """Bank payment receipts uploaded by users for manual verification"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bank_receipts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bank_receipts')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='bank_receipts', null=True, blank=True)
    registration_type = models.ForeignKey(EventRegistrationType, on_delete=models.SET_NULL, null=True, blank=True)

    # Receipt details
    receipt_image = models.ImageField(upload_to='bank_receipts/', help_text='Upload payment receipt/screenshot')
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text='Amount paid')
    transaction_id = models.CharField(max_length=200, blank=True, help_text='Transaction/Reference ID from bank')
    payment_date = models.DateField(help_text='Date of payment')
    notes = models.TextField(blank=True, help_text='Additional notes from user')

    # Status and review
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_receipts'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, help_text='Reason for rejection')

    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Bank Payment Receipt'
        verbose_name_plural = 'Bank Payment Receipts'

    def __str__(self):
        return f"{self.user.email} - {self.event.title} - {self.status}"

    def approve(self, reviewer):
        """Approve receipt and confirm registration"""
        self.status = 'approved'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()

        # Update registration status if exists
        if self.registration:
            self.registration.status = 'confirmed'
            self.registration.payment_status = 'paid'
            self.registration.payment_amount = self.amount
            self.registration.payment_date = timezone.now()
            self.registration.save()

    def reject(self, reviewer, reason):
        """Reject receipt"""
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save()


class RegistrationLog(models.Model):
    """Comprehensive logging for self-registration activities"""
    ACTION_CHOICES = [
        ('page_visit', 'Page Visited'),
        ('form_started', 'Form Started'),
        ('payment_method_selected', 'Payment Method Selected'),
        ('payment_initiated', 'Payment Initiated'),
        ('payment_success', 'Payment Successful'),
        ('payment_success_viewed', 'Payment Success Page Viewed'),
        ('payment_failed', 'Payment Failed'),
        ('registration_completed', 'Registration Completed'),
        ('registration_failed', 'Registration Failed'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('mwallet', 'JazzCash Mobile Wallet'),
        ('card', 'Debit/Credit Card'),
        ('bank', 'Offline Bank Transfer'),
        ('none', 'No Payment Required'),
    ]

    # Core fields
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registration_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='registration_logs')
    registration = models.ForeignKey(Registration, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')

    # Log details
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    # User information (captured at time of action)
    email = models.EmailField(blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    # Payment details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    transaction_reference = models.CharField(max_length=200, blank=True, help_text='JazzCash transaction reference or bank receipt ID')

    # Registration type
    registration_type = models.ForeignKey(EventRegistrationType, on_delete=models.SET_NULL, null=True, blank=True)

    # Technical details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, help_text='Browser/device information')

    # Additional context
    notes = models.TextField(blank=True, help_text='Additional details or error messages')
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional metadata as JSON')

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Registration Log'
        verbose_name_plural = 'Registration Logs'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['event', '-timestamp']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.event.title} - {self.action} - {self.email or 'Anonymous'} - {self.timestamp}"

    def get_action_badge_class(self):
        """Return Bootstrap badge class based on action"""
        badge_classes = {
            'page_visit': 'bg-info',
            'form_started': 'bg-primary',
            'payment_method_selected': 'bg-warning',
            'payment_initiated': 'bg-warning',
            'payment_success': 'bg-success',
            'payment_success_viewed': 'bg-success',
            'payment_failed': 'bg-danger',
            'registration_completed': 'bg-success',
            'registration_failed': 'bg-danger',
        }
        return badge_classes.get(self.action, 'bg-secondary')

    def get_payment_method_display_name(self):
        """Return friendly payment method name"""
        method_names = {
            'mwallet': 'JazzCash Mobile Wallet',
            'card': 'Debit/Credit Card',
            'bank': 'Offline Bank Transfer',
            'none': 'No Payment Required',
        }
        return method_names.get(self.payment_method, 'Unknown')
