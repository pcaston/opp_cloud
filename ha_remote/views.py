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
    """Show all available HA sites for the user"""
    # Get sites owned by the user
    sites = Site.objects.filter(user=request.user)
    print(f"Site status from DB: {[(site.name, site.ws_connected) for site in sites]}")
    
    return render(request, 'dashboard.html', {
        'sites': sites
    })

@login_required
def site_interface(request, site_id):
    """Interface for controlling a specific HA site"""
    site = get_object_or_404(Site, id=site_id)
    
    # Check if user is the owner
    if site.user != request.user:
        return HttpResponseForbidden("You don't have access to this Home Assistant site")
    
    return render(request, 'site_interface.html', {
        'site': site
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
    """Delete a site"""
    site = get_object_or_404(Site, id=site_id)
    
    # Check if user is the owner
    if site.user != request.user:
        messages.error(request, "You don't have permission to delete this site.")
        return redirect('dashboard')
    
    # Delete the site
    site_name = site.name
    site.delete()
    
    messages.success(request, f"Site '{site_name}' has been deleted.")
    return redirect('dashboard')