from django.db import models
from django.conf import settings
from django.utils import timezone


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    location = models.CharField(max_length=200)
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    max_attendees = models.IntegerField(default=100)
    image = models.ImageField(upload_to='events/', null=True, blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return self.title


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
    
    
