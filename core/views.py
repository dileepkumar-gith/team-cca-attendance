from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    """
    Shows a different message depending on the logged-in user's role.
    The @login_required decorator automatically redirects anyone
    not logged in to the login page — we don't have to check that manually.
    """
    return render(request, 'core/dashboard.html')