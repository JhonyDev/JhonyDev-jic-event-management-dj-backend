from django.shortcuts import render
from src.api.models import AppDownload

def download_app(request):
    """View for the app download page"""
    app = AppDownload.objects.filter(is_active=True).first()
    context = {
        'app': app
    }
    return render(request, 'download_app.html', context)
