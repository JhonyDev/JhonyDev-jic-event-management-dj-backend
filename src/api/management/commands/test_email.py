"""
Django Management Command to Test Email Configuration
====================================================

Usage:
    python manage.py test_email
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from src.api.email_utils import test_email_configuration


class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Testing email configuration...'))
        self.stdout.write(f'Email Host: {settings.EMAIL_HOST}')
        self.stdout.write(f'Email Port: {settings.EMAIL_PORT}')
        self.stdout.write(f'Email User: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'From Email: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write('')

        success, message = test_email_configuration()

        if success:
            self.stdout.write(self.style.SUCCESS(f'✓ {message}'))
            self.stdout.write(self.style.SUCCESS('Email configuration is working correctly!'))
        else:
            self.stdout.write(self.style.ERROR(f'✗ {message}'))
            self.stdout.write(self.style.ERROR('Email configuration failed!'))
