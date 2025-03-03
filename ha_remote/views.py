# ha_remote/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.models import Site

@login_required
def dashboard(request):
    # Get sites the user has access to
    sites = Site.objects.filter(user__username=request.user.username)
    return render(request, 'ha_remote/dashboard.html', {
        'sites': sites
    })

@login_required
def frontend(request, site_id):
    # Verify user has access to this site
    site = get_object_or_404(Site, id=site_id, user__username=request.user.username)
    return render(request, 'ha_remote/frontend.html', {
        'site': site,
        'ws_url': f"ws://{request.get_host()}/ws/opp_energy/",
    })