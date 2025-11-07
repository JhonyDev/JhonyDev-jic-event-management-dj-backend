from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.db import models
from datetime import timedelta
from .models import (
    Event, Agenda, AgendaTopic, AgendaCoordinator, Speaker, Session, LiveStreamURL,
    Exhibitor, ExhibitionArea, Registration, VenueMap, Sponsor, SupportingMaterial
)


class EventForm(forms.ModelForm):
    date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        })
    )
    end_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        })
    )

    class Meta:
        model = Event
        fields = [
            'title', 'description', 'date', 'end_date', 'location',
            'venue_details', 'max_attendees', 'image', 'status', 'allow_signup_without_qr',
            'is_paid_event', 'registration_fee', 'payment_methods'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'venue_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'max_attendees': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'allow_signup_without_qr': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_paid_event': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'registration_fee': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'payment_methods': forms.CheckboxSelectMultiple(choices=[('mwallet', 'Mobile Wallet (JazzCash)'), ('card', 'Credit/Debit Card')]),
        }
        help_texts = {
            'is_paid_event': 'Check this if attendees need to pay for event registration',
            'registration_fee': 'Registration fee in Pakistani Rupees (PKR)',
            'payment_methods': 'Select allowed payment methods for this event',
        }


class AgendaForm(forms.ModelForm):
    day_choice = forms.ChoiceField(
        choices=[],
        label="Event Day",
        help_text="Select which day of the event this agenda is for",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )

    class Meta:
        model = Agenda
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)

        if self.event:
            # Calculate the days between start and end date
            start_date = self.event.date.date()
            end_date = self.event.end_date.date() if self.event.end_date else start_date

            # Generate day choices
            day_choices = []
            current_date = start_date
            day_number = 1

            while current_date <= end_date:
                day_choices.append((current_date.isoformat(), f'Day {day_number} ({current_date.strftime("%B %d, %Y")})'))
                current_date += timedelta(days=1)
                day_number += 1

            # Add empty choice as first option for new agendas
            if not (self.instance and self.instance.pk):
                day_choices.insert(0, ('', '---------'))

            self.fields['day_choice'].choices = day_choices

            # If editing an existing agenda, set the day_choice based on current date
            if self.instance and self.instance.pk and self.instance.date:
                self.fields['day_choice'].initial = self.instance.date.isoformat()

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set the date based on the selected day
        if self.cleaned_data.get('day_choice'):
            from datetime import datetime
            instance.date = datetime.fromisoformat(self.cleaned_data['day_choice']).date()

        if commit:
            instance.save()
        return instance


class SpeakerForm(forms.ModelForm):
    class Meta:
        model = Speaker
        fields = [
            'name', 'email', 'bio', 'title', 'company',
            'photo', 'linkedin_url', 'twitter_url'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-control'}),
            'twitter_url': forms.URLInput(attrs={'class': 'form-control'}),
        }


class SessionForm(forms.ModelForm):
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        })
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        })
    )

    class Meta:
        model = Session
        fields = [
            'title', 'description', 'session_type', 'speakers',
            'start_time', 'end_time', 'location', 'max_attendees', 'materials_url',
            'allow_registration', 'slots_available', 'is_paid_session', 'session_fee', 'payment_methods'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'session_type': forms.Select(attrs={'class': 'form-select'}),
            'speakers': forms.CheckboxSelectMultiple(),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'max_attendees': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'materials_url': forms.URLInput(attrs={'class': 'form-control'}),
            'allow_registration': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'slots_available': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_paid_session': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'session_fee': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'payment_methods': forms.CheckboxSelectMultiple(choices=[('mwallet', 'Mobile Wallet (JazzCash)'), ('card', 'Credit/Debit Card')]),
        }
        help_texts = {
            'session_type': '<ul class="mb-0 ps-3"><li><strong>Keynote:</strong> Main featured presentation</li><li><strong>Workshop:</strong> Interactive hands-on session</li><li><strong>Panel:</strong> Group discussion with multiple speakers</li><li><strong>Networking:</strong> Social interaction time</li><li><strong>Break:</strong> Coffee/lunch break</li><li><strong>Presentation:</strong> Standard talk or lecture</li></ul>',
            'allow_registration': 'Allow attendees to register for this specific session',
            'slots_available': 'Number of available slots (leave empty for unlimited)',
            'is_paid_session': 'Check this if attendees need to pay to register for this session',
            'session_fee': 'Session registration fee in Pakistani Rupees (PKR)',
            'payment_methods': 'Select allowed payment methods for this session',
        }

    def __init__(self, *args, **kwargs):
        self.agenda = kwargs.pop('agenda', None)
        super().__init__(*args, **kwargs)
        if self.agenda:
            # Filter speakers to only show those related to this agenda's event
            self.fields['speakers'].queryset = Speaker.objects.filter(
                sessions__agenda__event=self.agenda.event
            ).distinct()

    def save(self, commit=True):
        instance = super().save(commit=False)
        # If this is a new session (no pk) and we have an agenda, set the order
        if not instance.pk and self.agenda:
            # Get the highest order value for this agenda and add 1
            max_order = Session.objects.filter(agenda=self.agenda).aggregate(
                max_order=models.Max('order')
            )['max_order'] or 0
            instance.order = max_order + 1

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class LiveStreamURLForm(forms.ModelForm):
    class Meta:
        model = LiveStreamURL
        fields = ['stream_url', 'platform']
        widgets = {
            'stream_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://youtube.com/watch?v=...'
            }),
            'platform': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'stream_url': 'Live Stream URL',
            'platform': 'Platform',
        }
        help_texts = {
            'stream_url': 'Enter the full URL of the live stream',
            'platform': 'Select the streaming platform',
        }


class ExhibitorForm(forms.ModelForm):
    class Meta:
        model = Exhibitor
        fields = [
            'company_name', 'contact_person', 'email', 'phone', 'website',
            'description', 'logo', 'booth_number', 'booth_size', 'special_requirements'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'booth_number': forms.TextInput(attrs={'class': 'form-control'}),
            'booth_size': forms.TextInput(attrs={'class': 'form-control'}),
            'special_requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ExhibitionAreaForm(forms.ModelForm):
    class Meta:
        model = ExhibitionArea
        fields = ['name', 'floor_plan', 'total_booths', 'booth_price', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'floor_plan': forms.FileInput(attrs={'class': 'form-control'}),
            'total_booths': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'booth_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class SelfRegistrationForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        label='Phone Number',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '03xxxxxxxxx',
            'pattern': '03[0-9]{9}',
            'title': 'Phone number must be 11 digits starting with 03'
        })
    )
    designation = forms.CharField(
        max_length=200,
        required=False,
        label='Designation',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Professor, Software Engineer, Student'
        })
    )
    affiliations = forms.CharField(
        max_length=300,
        required=False,
        label='Affiliation / Organization',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your university, company, or organization'
        })
    )
    address = forms.CharField(
        required=False,
        label='Address',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Your mailing address'
        })
    )
    country = forms.CharField(
        max_length=100,
        required=False,
        label='Country',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Pakistan, United States, United Kingdom'
        })
    )
    registration_type = forms.ChoiceField(
        label='Registration Type',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        required=False
    )
    workshops = forms.MultipleChoiceField(
        label='Select Workshop(s)',
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=True
    )

    def __init__(self, *args, **kwargs):
        event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)

        # Dynamically set registration type choices
        if event:
            from .models import EventRegistrationType
            reg_types = EventRegistrationType.objects.filter(event=event, is_active=True).order_by('order')
            if reg_types.exists():
                self.fields['registration_type'].choices = [('', '--- Select Registration Type ---')] + [
                    (str(rt.id), f"{rt.name} - PKR {rt.amount}" if rt.is_paid and rt.amount > 0 else rt.name)
                    for rt in reg_types
                ]
                self.fields['registration_type'].required = True
            else:
                # Hide registration type if no types defined
                self.fields['registration_type'].widget = forms.HiddenInput()

            # Set workshop choices from event's workshop sessions
            workshop_sessions = Session.objects.filter(
                agenda__event=event,
                session_type='workshop',
                allow_registration=True
            ).order_by('agenda__order', 'start_time')

            if workshop_sessions.exists():
                self.fields['workshops'].choices = [
                    (str(ws.id), f"{ws.title} ({ws.start_time.strftime('%I:%M %p')} - {ws.location or 'TBD'})")
                    for ws in workshop_sessions
                ]
            else:
                # Hide workshops field if no workshops available
                self.fields['workshops'].widget = forms.HiddenInput()

    def clean_email(self):
        email = self.cleaned_data['email']
        # Add any email validation logic here
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number', '').strip()

        # Check if phone number is 11 digits
        if len(phone_number) != 11:
            raise forms.ValidationError('Phone number must be exactly 11 digits.')

        # Check if it starts with '03'
        if not phone_number.startswith('03'):
            raise forms.ValidationError('Phone number must start with 03.')

        # Check if all characters are digits
        if not phone_number.isdigit():
            raise forms.ValidationError('Phone number must contain only digits.')

        return phone_number


class AgendaTopicForm(forms.ModelForm):
    class Meta:
        model = AgendaTopic
        fields = ['name', 'description', 'color', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }


class AgendaCoordinatorForm(forms.ModelForm):
    class Meta:
        model = AgendaCoordinator
        fields = ['name', 'email', 'phone', 'role']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.TextInput(attrs={'class': 'form-control'}),
        }


class VenueMapForm(forms.ModelForm):
    class Meta:
        model = VenueMap
        fields = ['title', 'description', 'image', 'order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Main Entrance Map, Conference Hall Direction'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description of what this map shows...'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 1
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        help_texts = {
            'image': 'Upload a clear image of the venue map or floor plan',
            'order': 'Lower numbers will be displayed first',
        }


class SponsorForm(forms.ModelForm):
    class Meta:
        model = Sponsor
        fields = ['title', 'description', 'logo', 'website', 'email', 'phone']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company/Sponsor name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about this sponsor...'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.example.com'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contact@sponsor.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 (555) 123-4567'
            }),
        }
        help_texts = {
            'logo': 'Upload sponsor logo (PNG, JPG, GIF)',
            'website': 'Sponsor website URL (optional)',
            'email': 'Contact email for sponsor (optional)',
            'phone': 'Contact phone for sponsor (optional)',
        }


class SupportingMaterialForm(forms.ModelForm):
    # Add multiple files field for galleries
    # Note: We'll handle multiple files via JavaScript, as Django's FileInput doesn't support multiple natively
    gallery_files = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,video/*',
            'style': 'display: none;',  # Hidden by default, shown via JavaScript for gallery type
            'id': 'gallery-files-input'
        }),
        help_text='Upload multiple images and videos for the gallery'
    )

    class Meta:
        model = SupportingMaterial
        fields = ['title', 'description', 'material_type', 'file', 'is_public', 'order', 'sessions']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Material title (e.g., Presentation Slides, Demo Guide)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of this material...'
            }),
            'material_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'material-type-select'  # Add ID for JavaScript targeting
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.ppt,.pptx,.doc,.docx,.txt,.jpg,.jpeg,.png,.gif,.mp4,.avi,.mov,.zip,.rar',
                'id': 'single-file-input'  # Add ID for JavaScript targeting
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 1
            }),
            'sessions': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'multiple': True
            }),
        }
        help_texts = {
            'file': 'Upload supporting material (PDF, PowerPoint, Word, Images, Videos, Archives)',
            'is_public': 'Make this material visible to all attendees',
            'order': 'Display order (lower numbers appear first)',
            'sessions': 'Select sessions this material is associated with',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make file field not required since galleries won't use it
        self.fields['file'].required = False

    def clean(self):
        cleaned_data = super().clean()
        material_type = cleaned_data.get('material_type')
        file = cleaned_data.get('file')

        # For galleries, we'll handle file validation in the view
        # since Django forms don't support multiple file uploads natively
        if material_type != 'gallery':
            if not file and not self.instance.pk:  # Only require file for new non-gallery materials
                raise forms.ValidationError('Please upload a file for this material type.')

        return cleaned_data
