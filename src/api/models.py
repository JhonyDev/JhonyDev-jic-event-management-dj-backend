from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


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

    class Meta:
        unique_together = ['event', 'user']
        ordering = ['-registered_at']

    def __str__(self):
        return f"{self.user.username} - {self.event.title}"


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
