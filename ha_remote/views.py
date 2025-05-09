# ha_remote/views.py
import json
import logging
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from core.models import Site

# Get logger
_LOGGER = logging.getLogger(__name__)

@login_required
def dashboard(request):
    """Show all available HA sites for the user"""
    # Get sites owned by the user
    sites = Site.objects.filter(user=request.user)
    
    # The connection status is already stored in the Site model
    # No need to check it again here
    
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
    
    # We don't need to check for coordinator here - that happens when
    # the WebSocket connection is established
    
    return render(request, 'site_interface.html', {
        'site': site
    })

@login_required
def site_status(request, site_id):
    """Check if a site has an active WebSocket connection."""
    site = get_object_or_404(Site, id=site_id, user=request.user)
    
    # The site's connection status is stored in the database
    # Just return that value
    
    return JsonResponse({
        'id': site.id,
        'name': site.name,
        'connected': site.ws_connected,
        'last_connected': site.last_connected.isoformat() if site.last_connected else None
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

@login_required
def refresh_connection(request, site_id):
    """Attempt to refresh the Home Assistant connection for a site."""
    site = get_object_or_404(Site, id=site_id, user=request.user)
    
    try:
        # Use Channels to send a message to the OppEnergyConsumer
        channel_layer = get_channel_layer()
        
        # Send to the site group
        site_group = f"site_{site_id}"
        async_to_sync(channel_layer.group_send)(
            site_group,
            {
                "type": "check_connection",
                "site_id": site_id
            }
        )
        
        messages.success(request, f"Connection refresh requested for {site.name}")
    except Exception as e:
        _LOGGER.error(f"Error refreshing connection: {str(e)}")
        messages.error(request, f"Could not refresh connection: {str(e)}")
    
    return redirect('site_interface', site_id=site_id)