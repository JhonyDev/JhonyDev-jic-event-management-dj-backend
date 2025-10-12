from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password"""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)

        # Auto-generate username from email if not provided
        if 'username' not in extra_fields or not extra_fields['username']:
            extra_fields['username'] = email

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


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
    REQUIRED_FIELDS = []  # Remove required fields for superuser creation

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Auto-generate username from email if not set
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)
