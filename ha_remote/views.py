# ha_remote/views.py
import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

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

@login_required
def site_status(request, site_id):
    """Check if a site has an active WebSocket connection."""
    site = get_object_or_404(Site, id=site_id, user=request.user)
    
    # For now, assume a site is connected if it exists
    # Later, you can implement actual connection status tracking
    return JsonResponse({
        'id': site.id,
        'name': site.name,
        'connected': True,  # Temporarily assume always connected
        'last_connected': datetime.now().isoformat() if hasattr(site, 'last_connected') else None
    })

@login_required
def delete_site(request, site_id):
    """Delete a site that belongs to the current user."""
    site = get_object_or_404(Site, id=site_id, user=request.user)
    
    if request.method == 'POST':
        site_name = site.name
        site.delete()
        messages.success(request, f'Site "{site_name}" has been deleted.')
        return redirect('ha_dashboard')
    
    return render(request, 'ha_remote/confirm_delete.html', {
        'site': site
    })