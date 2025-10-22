"""
Management command to send a test registration approval email
Usage: python manage.py send_test_approval_email --email user@example.com --event-id 1
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from src.api.models import Event, Registration
from src.api.email_utils import send_registration_approval_email

User = get_user_model()


class Command(BaseCommand):
    help = 'Send a test registration approval email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email address to send the test email to',
            required=True
        )
        parser.add_argument(
            '--event-id',
            type=int,
            help='Event ID to use for the test email',
            required=True
        )

    def handle(self, *args, **options):
        email = options['email']
        event_id = options['event_id']

        try:
            # Get or create a test user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': 'Test',
                    'last_name': 'User',
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created test user: {user.email}'))

            # Get the event
            try:
                event = Event.objects.get(pk=event_id)
            except Event.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Event with ID {event_id} does not exist'))
                return

            # Get or create a registration
            registration, created = Registration.objects.get_or_create(
                event=event,
                user=user,
                defaults={
                    'status': 'confirmed',
                    'payment_status': 'paid',
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created test registration: {registration.registration_id}'))

            # Send the email
            self.stdout.write(self.style.WARNING(f'Sending approval email to {user.email}...'))
            success, message = send_registration_approval_email(
                user=user,
                event=event,
                registration=registration
            )

            if success:
                self.stdout.write(self.style.SUCCESS(f'✓ {message}'))
                self.stdout.write(self.style.SUCCESS(f'Registration ID: {registration.registration_id}'))
                self.stdout.write(self.style.SUCCESS(f'Event: {event.title}'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ {message}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
