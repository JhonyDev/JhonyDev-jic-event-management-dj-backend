from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Event, Registration, Announcement, AppContent, FAQ, ContactInfo,
    Agenda, Session, Speaker, SupportingMaterial, SupportingMaterialFile, QuickAction, LiveStreamURL
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class UserProfileSerializer(serializers.ModelSerializer):
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile_image', 'profile_image_url', 'date_joined']
        read_only_fields = ['id', 'username', 'date_joined']

    def get_profile_image_url(self, obj):
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None


class ExternalRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for external registration without password"""
    workshop_selection = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'designation',
            'affiliations', 'address', 'country', 'phone_number',
            'registration_type', 'workshop_selection'
        ]

    def create(self, validated_data):
        # Remove workshop_selection from validated_data (we'll handle it separately)
        workshop_selection = validated_data.pop('workshop_selection', None)

        # Create user with phone number as password
        email = validated_data.get('email')
        phone_number = validated_data.get('phone_number')

        user = User.objects.create(
            username=email,
            email=email,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            designation=validated_data.get('designation'),
            affiliations=validated_data.get('affiliations'),
            address=validated_data.get('address'),
            country=validated_data.get('country'),
            phone_number=phone_number,
            registration_type=validated_data.get('registration_type')
        )

        # Set phone number as password if provided, otherwise set unusable password
        if phone_number:
            user.set_password(phone_number)
        else:
            user.set_unusable_password()
        user.save()

        # Store workshop_selection for later use in the view
        user._workshop_selection = workshop_selection

        return user


class RegistrationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Registration
        fields = ['id', 'event', 'user', 'registered_at', 'status']
        read_only_fields = ['id', 'registered_at']


class EventSerializer(serializers.ModelSerializer):
    organizer = UserSerializer(read_only=True)
    registrations_count = serializers.SerializerMethodField()
    is_registered = serializers.SerializerMethodField()
    registration_status = serializers.SerializerMethodField()
    hold_expires_at = serializers.SerializerMethodField()
    hold_time_remaining = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    registration_type_amount = serializers.SerializerMethodField()
    workshop_fee = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'date', 'location',
            'organizer', 'created_at', 'updated_at', 'max_attendees',
            'image', 'registrations_count', 'is_registered', 'registration_status', 'status',
            'allow_signup_without_qr', 'is_paid_event', 'registration_fee',
            'payment_methods', 'bank_details', 'hold_expires_at', 'hold_time_remaining',
            'total_amount', 'registration_type_amount', 'workshop_fee'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'organizer']

    def get_registrations_count(self, obj):
        return obj.registrations.filter(status='confirmed').count()

    def get_is_registered(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.registrations.filter(user=request.user).exists()
        return False

    def get_registration_status(self, obj):
        """Get user's registration status for this event (pending, confirmed, or None)"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            registration = obj.registrations.filter(user=request.user).first()
            if registration:
                return registration.status
        return None

    def get_hold_expires_at(self, obj):
        """Get hold expiration time for user's registration"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            registration = obj.registrations.filter(user=request.user, status='hold').first()
            if registration and registration.hold_expires_at:
                return registration.hold_expires_at.isoformat()
        return None

    def get_hold_time_remaining(self, obj):
        """Get seconds remaining until hold expires"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            registration = obj.registrations.filter(user=request.user, status='hold').first()
            if registration and registration.hold_expires_at:
                from django.utils import timezone
                remaining = (registration.hold_expires_at - timezone.now()).total_seconds()
                return max(0, int(remaining))  # Return 0 if already expired
        return None

    def get_total_amount(self, obj):
        """Get total amount for user's registration (base fee + registration type + workshop)"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            registration = obj.registrations.filter(user=request.user).first()
            if registration:
                total = float(obj.registration_fee or 0)
                # Add registration type fee
                if registration.registration_type and registration.registration_type.is_paid:
                    total += float(registration.registration_type.amount or 0)
                # Add workshop fees (using correct field names: is_paid_session and session_fee)
                for workshop in registration.selected_workshops.all():
                    if workshop.is_paid_session:
                        total += float(workshop.session_fee or 0)
                return total
        return None

    def get_registration_type_amount(self, obj):
        """Get registration type amount for user's registration"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            registration = obj.registrations.filter(user=request.user).first()
            if registration and registration.registration_type and registration.registration_type.is_paid:
                return float(registration.registration_type.amount or 0)
        return None

    def get_workshop_fee(self, obj):
        """Get total workshop fees for user's registration"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            registration = obj.registrations.filter(user=request.user).first()
            if registration:
                total_workshop_fee = 0
                for workshop in registration.selected_workshops.all():
                    if workshop.is_paid_session:
                        total_workshop_fee += float(workshop.session_fee or 0)
                return total_workshop_fee if total_workshop_fee > 0 else None
        return None


class EventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'date', 'location', 'max_attendees',
            'image', 'allow_signup_without_qr', 'is_paid_event',
            'registration_fee', 'payment_methods'
        ]


class AnnouncementSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'content', 'type', 'event', 'event_title',
            'priority', 'author', 'author_name', 'is_active',
            'created_at', 'updated_at', 'publish_date', 'expire_date'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def get_author_name(self, obj):
        if obj.author:
            return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.username
        return None


class AppContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppContent
        fields = [
            'id', 'content_type', 'title', 'content',
            'version', 'last_updated', 'created_at'
        ]


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = [
            'id', 'question', 'answer', 'category', 'order'
        ]


class ContactInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfo
        fields = [
            'id', 'contact_type', 'label', 'value', 'order'
        ]


class SpeakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Speaker
        fields = [
            'id', 'name', 'email', 'bio', 'title', 'company',
            'photo', 'linkedin_url', 'twitter_url'
        ]


class LiveStreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveStreamURL
        fields = ['id', 'stream_url', 'platform']


class SessionSerializer(serializers.ModelSerializer):
    speakers = SpeakerSerializer(many=True, read_only=True)
    live_stream_urls = LiveStreamSerializer(many=True, read_only=True)
    start_time_formatted = serializers.SerializerMethodField()
    end_time_formatted = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    is_registered = serializers.SerializerMethodField()
    registrations_count = serializers.SerializerMethodField()
    # Add aliases for frontend compatibility
    is_paid = serializers.BooleanField(source='is_paid_session', read_only=True)
    fee = serializers.DecimalField(source='session_fee', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Session
        fields = [
            'id', 'title', 'description', 'session_type', 'speakers',
            'start_time', 'end_time', 'start_time_formatted', 'end_time_formatted',
            'duration', 'location', 'max_attendees', 'materials_url', 'order',
            'allow_registration', 'slots_available', 'is_paid_session',
            'session_fee', 'payment_methods', 'is_registered', 'registrations_count',
            'live_stream_urls', 'is_paid', 'fee'
        ]

    def get_is_registered(self, obj):
        """Check if current user is registered for this session"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from .models import SessionRegistration
            return SessionRegistration.objects.filter(
                session=obj,
                user=request.user
            ).exists()
        return False

    def get_registrations_count(self, obj):
        """Get count of registered users for this session"""
        return obj.registrations.count()

    def get_start_time_formatted(self, obj):
        """Format start time for mobile app (e.g., '09:00 AM')"""
        if obj.start_time:
            return obj.start_time.strftime('%I:%M %p')
        return None

    def get_end_time_formatted(self, obj):
        """Format end time for mobile app (e.g., '10:00 AM')"""
        if obj.end_time:
            return obj.end_time.strftime('%I:%M %p')
        return None

    def get_duration(self, obj):
        """Calculate duration between start and end time"""
        if obj.start_time and obj.end_time:
            from datetime import datetime, date
            start = datetime.combine(date.today(), obj.start_time)
            end = datetime.combine(date.today(), obj.end_time)
            duration = end - start
            total_minutes = int(duration.total_seconds() / 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60

            if hours > 0:
                return f"{hours}h {minutes}min" if minutes > 0 else f"{hours}h"
            else:
                return f"{minutes}min"
        return None


class AgendaSerializer(serializers.ModelSerializer):
    sessions = SessionSerializer(many=True, read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)
    sessions_count = serializers.SerializerMethodField()

    class Meta:
        model = Agenda
        fields = [
            'id', 'title', 'description', 'date', 'order',
            'event_title', 'sessions', 'sessions_count', 'day_number'
        ]

    def get_sessions_count(self, obj):
        return obj.sessions.count()


class AgendaSessionSerializer(serializers.Serializer):
    """
    Serializer to format agenda data for mobile app timeline view.
    Combines agenda sessions into a flat list with proper formatting.
    """
    id = serializers.IntegerField()
    time = serializers.CharField()  # Formatted time like "09:00 AM"
    duration = serializers.CharField()  # Formatted duration like "30 min"
    title = serializers.CharField()
    description = serializers.CharField()
    location = serializers.CharField()
    type = serializers.CharField()  # session_type
    speaker = serializers.CharField(required=False)  # Main speaker name


class SupportingMaterialSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = SupportingMaterial
        fields = [
            'id', 'title', 'description', 'material_type', 'file', 'file_url',
            'is_public', 'created_at'
        ]

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class SupportingMaterialFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    media_type = serializers.SerializerMethodField()

    class Meta:
        model = SupportingMaterialFile
        fields = ['id', 'file', 'file_url', 'media_type', 'uploaded_at']

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def get_media_type(self, obj):
        return obj.get_media_type()


class QuickActionSerializer(serializers.ModelSerializer):
    supporting_materials = SupportingMaterialSerializer(many=True, read_only=True)
    supporting_materials_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=SupportingMaterial.objects.all(),
        source='supporting_materials',
        required=False
    )
    icon_class = serializers.CharField(source='get_icon_class', read_only=True)
    materials_count = serializers.SerializerMethodField()
    icon_type = serializers.CharField(source='icon', read_only=True)  # Add icon_type for React Native
    description = serializers.CharField(source='info_line', read_only=True)  # Map info_line to description

    class Meta:
        model = QuickAction
        fields = [
            'id', 'event', 'title', 'icon', 'icon_type', 'icon_class', 'info_line', 'description',
            'supporting_materials', 'supporting_materials_ids',
            'materials_count', 'order', 'is_active'
        ]

    def get_materials_count(self, obj):
        return obj.supporting_materials.filter(is_public=True).count()

    def create(self, validated_data):
        materials = validated_data.pop('supporting_materials', [])
        quick_action = QuickAction.objects.create(**validated_data)
        quick_action.supporting_materials.set(materials)
        return quick_action

    def update(self, instance, validated_data):
        materials = validated_data.pop('supporting_materials', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if materials is not None:
            instance.supporting_materials.set(materials)
        return instance