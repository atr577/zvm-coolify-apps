"""
Views for the apps application.
"""
import requests
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings


@login_required
def index(request):
    """Main page with button to run dummy app."""
    context = {
        'result': None,
        'error': None,
    }
    
    if request.method == 'POST' and 'run_dummy_app' in request.POST:
        try:
            # Call dummy app
            response = requests.get(
                f"{settings.DUMMY_APP_URL}/get_tables",
                timeout=10
            )
            response.raise_for_status()
            context['result'] = response.text
            messages.success(request, 'Dummy app executed successfully!')
        except requests.exceptions.RequestException as e:
            context['error'] = str(e)
            messages.error(request, f'Error calling dummy app: {e}')
    
    return render(request, 'apps/index.html', context)
