from django import forms
from .models import Event
from django.contrib.auth.forms import AuthenticationForm

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["title", "description", "date", "location"]

class LoginForm(AuthenticationForm):
    pass


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["title", "description", "date", "location"]

class LoginForm(AuthenticationForm):
    pass


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'location']

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
