from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Event, Registration


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


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

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'date', 'location',
            'organizer', 'created_at', 'updated_at', 'max_attendees',
            'image', 'registrations_count', 'is_registered'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'organizer']

    def get_registrations_count(self, obj):
        return obj.registrations.filter(status='confirmed').count()

    def get_is_registered(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.registrations.filter(user=request.user).exists()
        return False


class EventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'location', 'max_attendees', 'image']