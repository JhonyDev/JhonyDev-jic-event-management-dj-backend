from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    designation = models.CharField(max_length=200, blank=True, null=True, default=None)
    affiliations = models.CharField(max_length=300, blank=True, null=True, default=None)
    address = models.TextField(blank=True, null=True, default=None)
    country = models.CharField(max_length=100, blank=True, null=True, default=None)
    phone_number = models.CharField(max_length=20, blank=True, null=True, default=None)
    registration_type = models.CharField(max_length=100, blank=True, null=True, default=None)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email
