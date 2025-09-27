#!/usr/bin/env python
import os
import django
import sys

# Add the project directory to the Python path
sys.path.append('/home/jhonydev/Repositories/JIC - Event Management App/django-backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from src.api.models import AppContent, FAQ, ContactInfo

def create_sample_data():
    # Create Privacy Policy content
    privacy_policy, created = AppContent.objects.get_or_create(
        content_type='privacy_policy',
        defaults={
            'title': 'Privacy & Security Policy',
            'content': '''
JIC Event Management is committed to protecting your privacy and ensuring the security of your personal information.

**Information We Collect:**
• Personal information provided during registration (name, email, phone)
• Profile information and preferences
• Event attendance and participation data
• Usage analytics and app interaction data

**How We Use Your Information:**
• To provide and improve our event management services
• To send event notifications and announcements
• To personalize your app experience
• To ensure security and prevent fraud

**Data Security:**
We implement industry-standard security measures to protect your data, including encryption, secure servers, and regular security audits.

**Your Rights:**
• Access and update your personal information
• Request data deletion (right to be forgotten)
• Opt-out of non-essential communications
• Export your data in portable format

**Contact Us:**
For any privacy-related questions, contact us at privacy@jic-events.com.

This policy is effective as of September 2025 and may be updated periodically.
            ''',
            'version': '1.0',
            'is_active': True
        }
    )

    # Create Help & Support content
    help_support, created = AppContent.objects.get_or_create(
        content_type='help_support',
        defaults={
            'title': 'Help & Support',
            'content': '''
Welcome to JIC Event Management Help Center. We're here to help you make the most of your event experience.

**Getting Started:**
1. Download and install the JIC Events app
2. Create your account with a valid email address
3. Complete your profile to get personalized event recommendations
4. Browse and register for events that interest you

**Common Issues:**
• **Login Problems:** Reset your password using the "Forgot Password" link
• **Event Registration:** Ensure you meet event requirements and have a stable internet connection
• **Profile Updates:** Changes may take a few minutes to reflect across the app
• **Notifications:** Check your device settings to ensure notifications are enabled

**Features Guide:**
• **Event Discovery:** Browse events by date, category, or location
• **Registration:** Quick one-tap registration with confirmation
• **Announcements:** Stay updated with event-specific announcements
• **Profile Management:** Update your information and preferences anytime

**Need More Help?**
Our support team is available 24/7 to assist you with any questions or issues.
            ''',
            'version': '1.0',
            'is_active': True
        }
    )

    # Create About content
    about, created = AppContent.objects.get_or_create(
        content_type='about',
        defaults={
            'title': 'About JIC Event Management',
            'content': '''
JIC Event Management is a comprehensive platform designed to streamline event discovery, registration, and management for both organizers and participants.

**Our Mission:**
To connect people with meaningful events and experiences while providing organizers with powerful tools to manage their events effectively.

**What We Offer:**
• **For Participants:**
  - Easy event discovery and search
  - One-click registration process
  - Real-time event announcements
  - Personal event calendar
  - Social features and networking

• **For Organizers:**
  - Complete event management suite
  - Registration and ticketing system
  - Attendee communication tools
  - Analytics and reporting
  - Marketing and promotion tools

**Our Story:**
Founded in 2025, JIC Event Management emerged from the need to simplify event management in the digital age. Our team combines expertise in technology, event planning, and user experience to create intuitive solutions.

**Core Values:**
• Innovation in event technology
• User-centric design and experience
• Privacy and data security
• Community building and connection
• Accessibility and inclusivity

**Technology:**
Built with modern technologies including React Native for mobile apps and Django for robust backend services, ensuring reliable and scalable event management.

Thank you for being part of the JIC Event Management community!
            ''',
            'version': '1.0',
            'is_active': True
        }
    )

    # Create sample FAQs
    faqs = [
        {
            'question': 'How do I register for an event?',
            'answer': 'Browse events in the app, tap on an event you\'re interested in, and click the "Register" button. You\'ll receive a confirmation email once registered.',
            'category': 'registration'
        },
        {
            'question': 'Can I cancel my event registration?',
            'answer': 'Yes, you can cancel your registration up to 24 hours before the event start time. Go to your profile, find the event under "My Events" and select "Cancel Registration".',
            'category': 'registration'
        },
        {
            'question': 'How do I update my profile information?',
            'answer': 'Go to the Profile tab, tap "Edit Profile", update your information, and save changes. Profile updates are reflected immediately.',
            'category': 'account'
        },
        {
            'question': 'Why am I not receiving event notifications?',
            'answer': 'Check your device notification settings and ensure the JIC Events app has permission to send notifications. Also verify your notification preferences in the app settings.',
            'category': 'technical'
        },
        {
            'question': 'How do I find events near me?',
            'answer': 'The app automatically shows events based on your location (if location permission is granted). You can also manually search by city or location.',
            'category': 'events'
        },
        {
            'question': 'Is my personal information secure?',
            'answer': 'Yes, we use industry-standard encryption and security measures to protect your data. See our Privacy Policy for detailed information.',
            'category': 'general'
        },
    ]

    for faq_data in faqs:
        FAQ.objects.get_or_create(
            question=faq_data['question'],
            defaults={
                'answer': faq_data['answer'],
                'category': faq_data['category'],
                'is_active': True
            }
        )

    # Create sample contact information
    contacts = [
        {
            'contact_type': 'email',
            'label': 'General Support',
            'value': 'support@jic-events.com',
            'order': 1
        },
        {
            'contact_type': 'email',
            'label': 'Technical Support',
            'value': 'tech@jic-events.com',
            'order': 2
        },
        {
            'contact_type': 'phone',
            'label': 'Support Hotline',
            'value': '+1 (555) 123-4567',
            'order': 3
        },
        {
            'contact_type': 'address',
            'label': 'Main Office',
            'value': '123 Event Street, City, State 12345',
            'order': 4
        },
        {
            'contact_type': 'social_media',
            'label': 'Twitter',
            'value': 'https://twitter.com/jicevents',
            'order': 5
        },
    ]

    for contact_data in contacts:
        ContactInfo.objects.get_or_create(
            contact_type=contact_data['contact_type'],
            label=contact_data['label'],
            defaults={
                'value': contact_data['value'],
                'order': contact_data['order'],
                'is_active': True
            }
        )

    print("Sample data created successfully!")
    print(f"AppContent objects: {AppContent.objects.count()}")
    print(f"FAQ objects: {FAQ.objects.count()}")
    print(f"ContactInfo objects: {ContactInfo.objects.count()}")

if __name__ == '__main__':
    create_sample_data()