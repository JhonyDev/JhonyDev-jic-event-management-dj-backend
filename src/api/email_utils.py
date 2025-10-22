"""
Email Utility Functions for Event Registration System
====================================================

This module provides utility functions for sending emails to event attendees.
"""

import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)


def send_registration_success_email(user, event, registration, transaction=None, workshops=None):
    """
    Send a registration success email to the user.

    Args:
        user: The User object who registered
        event: The Event object
        registration: The Registration object
        transaction: Optional JazzCashTransaction object with payment details
        workshops: Optional list of selected workshops

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Prepare context for email templates
        context = {
            'user': user,
            'event': event,
            'registration': registration,
            'transaction': transaction,
            'workshops': workshops or [],
        }

        # Render email templates
        subject = f"Registration Confirmed - {event.title}"
        html_content = render_to_string('emails/registration_success.html', context)
        text_content = render_to_string('emails/registration_success.txt', context)

        # Prepare email
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email

        # Create email message
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email],
        )

        # Attach HTML version
        email.attach_alternative(html_content, "text/html")

        # Send email
        email.send(fail_silently=False)

        logger.info(f"Registration success email sent to {to_email} for event {event.title}")
        return True, f"Email sent successfully to {to_email}"

    except Exception as e:
        logger.error(f"Failed to send registration email to {user.email}: {str(e)}", exc_info=True)
        return False, f"Failed to send email: {str(e)}"


def send_bank_transfer_pending_email(user, event, registration, receipt):
    """
    Send an email when bank transfer receipt is submitted and pending approval.

    Args:
        user: The User object who registered
        event: The Event object
        registration: The Registration object
        receipt: The BankPaymentReceipt object

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        context = {
            'user': user,
            'event': event,
            'registration': registration,
            'receipt': receipt,
        }

        subject = f"Registration Pending - {event.title}"

        # Simple text email for pending status
        text_content = f"""
Dear {user.first_name} {user.last_name},

Thank you for your registration for {event.title}.

Your bank transfer receipt has been submitted and is pending approval by the event organizers.

SUBMISSION DETAILS:
-------------------
Event: {event.title}
Amount: PKR {receipt.amount}
Receipt ID: {receipt.id}
Submission Date: {receipt.created_at.strftime('%B %d, %Y %H:%M')}

You will receive a confirmation email once your payment has been verified and approved.

If you have any questions, please contact the event organizers.

Best regards,
{event.title} Team

---
This is an automated message. Please do not reply to this email.
        """.strip()

        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email],
        )

        email.send(fail_silently=False)

        logger.info(f"Bank transfer pending email sent to {to_email} for event {event.title}")
        return True, f"Email sent successfully to {to_email}"

    except Exception as e:
        logger.error(f"Failed to send bank transfer pending email to {user.email}: {str(e)}", exc_info=True)
        return False, f"Failed to send email: {str(e)}"


def send_registration_approval_email(user, event, registration):
    """
    Send an email when a user's registration is approved by the event organizer.

    Args:
        user: The User object who registered
        event: The Event object
        registration: The Registration object

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        context = {
            'user': user,
            'event': event,
            'registration': registration,
        }

        subject = f"Registration Approved - {event.title}"
        html_content = render_to_string('emails/registration_approval.html', context)
        text_content = render_to_string('emails/registration_approval.txt', context)

        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email],
        )

        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Registration approval email sent to {to_email} for event {event.title}")
        return True, f"Email sent successfully to {to_email}"

    except Exception as e:
        logger.error(f"Failed to send registration approval email to {user.email}: {str(e)}", exc_info=True)
        return False, f"Failed to send email: {str(e)}"


def test_email_configuration():
    """
    Test the email configuration by sending a test email.

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        from django.core.mail import send_mail

        subject = "Test Email - Event Registration System"
        message = "This is a test email to verify your email configuration is working correctly."
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = settings.DEFAULT_FROM_EMAIL  # Send to self for testing

        send_mail(
            subject,
            message,
            from_email,
            [to_email],
            fail_silently=False,
        )

        logger.info(f"Test email sent successfully to {to_email}")
        return True, f"Test email sent successfully to {to_email}"

    except Exception as e:
        logger.error(f"Failed to send test email: {str(e)}", exc_info=True)
        return False, f"Failed to send test email: {str(e)}"
