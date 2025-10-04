from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.db import models
from datetime import timedelta
from .models import (
    Event, Agenda, AgendaTopic, AgendaCoordinator, Speaker, Session,
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
            'venue_details', 'max_attendees', 'image', 'status', 'allow_signup_without_qr'
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
            'start_time', 'end_time', 'location', 'max_attendees', 'materials_url'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'session_type': forms.Select(attrs={'class': 'form-select'}),
            'speakers': forms.CheckboxSelectMultiple(),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'max_attendees': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'materials_url': forms.URLInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'session_type': '<ul class="mb-0 ps-3"><li><strong>Keynote:</strong> Main featured presentation</li><li><strong>Workshop:</strong> Interactive hands-on session</li><li><strong>Panel:</strong> Group discussion with multiple speakers</li><li><strong>Networking:</strong> Social interaction time</li><li><strong>Break:</strong> Coffee/lunch break</li><li><strong>Presentation:</strong> Standard talk or lecture</li></ul>',
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
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        # Add any email validation logic here
        return email


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
                'class': 'form-select'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.ppt,.pptx,.doc,.docx,.txt,.jpg,.jpeg,.png,.gif,.mp4,.avi,.mov,.zip,.rar'
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
