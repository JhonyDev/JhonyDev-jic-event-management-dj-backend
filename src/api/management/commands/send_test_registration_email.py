"""
Django Management Command to Send Test Registration Email
========================================================

Usage:
    python manage.py send_test_registration_email --email user@example.com
    python manage.py send_test_registration_email --email user@example.com --event-id 1
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from src.api.models import Event, Registration
from src.api.email_utils import send_registration_success_email


User = get_user_model()


class Command(BaseCommand):
    help = 'Send a test registration confirmation email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email address to send the test to',
            required=True
        )
        parser.add_argument(
            '--event-id',
            type=int,
            help='Event ID to use (optional, will use first available event if not provided)',
            required=False
        )

    def handle(self, *args, **options):
        email = options['email']
        event_id = options.get('event_id')

        self.stdout.write(self.style.WARNING(f'Preparing test registration email for {email}...'))

        # Get or create a test event
        if event_id:
            try:
                event = Event.objects.get(pk=event_id)
            except Event.DoesNotExist:
                raise CommandError(f'Event with ID {event_id} does not exist')
        else:
            event = Event.objects.first()
            if not event:
                raise CommandError('No events found in the database. Please create an event first.')

        self.stdout.write(f'Using event: {event.title}')

        # Create or get a test user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'first_name': 'Test',
                'last_name': 'User',
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created test user: {user.email}'))
        else:
            self.stdout.write(f'Using existing user: {user.email}')

        # Create a mock registration object (not saving to DB)
        from datetime import datetime
        from decimal import Decimal

        # Create a temporary registration object (save it to DB for testing)
        registration, reg_created = Registration.objects.get_or_create(
            event=event,
            user=user,
            defaults={
                'status': 'confirmed',
                'payment_status': 'paid',
                'payment_amount': Decimal('5000.00')
            }
        )

        # Create a mock transaction object
        class MockTransaction:
            def __init__(self):
                self.amount = Decimal('5000.00')
                self.txn_ref_no = 'TEST-TXN-' + datetime.now().strftime('%Y%m%d%H%M%S')
                self.completed_at = datetime.now()
                self.txn_type = 'MPAY'

        mock_transaction = MockTransaction()

        # Get some workshops if available
        workshops = []
        try:
            workshops = list(event.sessions.filter(session_type='workshop')[:2])
        except Exception:
            pass

        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Sending test email...'))

        # Send the email
        success, message = send_registration_success_email(
            user=user,
            event=event,
            registration=registration,
            transaction=mock_transaction,
            workshops=workshops
        )

        self.stdout.write('')
        if success:
            self.stdout.write(self.style.SUCCESS(f'✓ {message}'))
            self.stdout.write(self.style.SUCCESS('Test email sent successfully!'))
            self.stdout.write(f'Check the inbox for: {email}')
        else:
            self.stdout.write(self.style.ERROR(f'✗ {message}'))
            self.stdout.write(self.style.ERROR('Failed to send test email!'))
