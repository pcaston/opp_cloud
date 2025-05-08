# ha_remote/views.py
import json
import logging
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Site

# Get logger
_LOGGER = logging.getLogger(__name__)

# Define your integration's domain constant here
OPP_ENERGY_DOMAIN = 'opp_energy'  # Replace with your actual domain

@login_required
def dashboard(request):
    """Show all available HA sites for the user"""
    # Get sites owned by the user
    sites = Site.objects.filter(user=request.user)
    
    # Check connection status if possible
    try:
        for site in sites:
            site.ws_connected = check_ha_connection(site)
    except Exception as e:
        _LOGGER.error(f"Error checking HA connection status: {str(e)}")
    
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
    
    # Check if coordinator is available (if Home Assistant is integrated)
    try:
        coordinator = get_site_coordinator(site)
        if not coordinator:
            messages.warning(request, f"Home Assistant integration for {site.name} is not connected.")
    except Exception as e:
        _LOGGER.error(f"Error checking coordinator: {str(e)}")
        messages.warning(request, "Could not verify Home Assistant connection status.")
    
    return render(request, 'site_interface.html', {
        'site': site
    })

@login_required
def site_status(request, site_id):
    """Check if a site has an active WebSocket connection."""
    site = get_object_or_404(Site, id=site_id, user=request.user)
    
    # Check actual connection status if possible
    connected = False
    try:
        connected = check_ha_connection(site)
    except Exception as e:
        _LOGGER.error(f"Error checking HA connection: {str(e)}")
    
    return JsonResponse({
        'id': site.id,
        'name': site.name,
        'connected': connected,
        'last_connected': datetime.now().isoformat() if connected else None
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

# Helper functions to interface with Home Assistant

def get_hass_instance():
    """
    Get the Home Assistant instance from the Django app config.
    Returns None if not available.
    """
    try:
        from django.apps import apps
        
        hass_app = apps.get_app_config('ha_remote')
        if hasattr(hass_app, 'hass'):
            return hass_app.hass
        
        _LOGGER.warning("Home Assistant instance not found in app config")
    except Exception as e:
        _LOGGER.error(f"Error retrieving Home Assistant instance: {str(e)}")
    
    return None

def get_site_coordinator(site):
    """
    Get the OppEnergyDataUpdateCoordinator for a site.
    Returns None if not found.
    """
    try:
        hass = get_hass_instance()
        if not hass:
            _LOGGER.warning("Home Assistant instance not available")
            return None
        
        # Look for the coordinator in the domain data
        if OPP_ENERGY_DOMAIN not in hass.data:
            _LOGGER.warning(f"Integration {OPP_ENERGY_DOMAIN} not loaded in Home Assistant")
            return None
        
        # Find coordinator matching the site
        domain_data = hass.data[OPP_ENERGY_DOMAIN]
        
        for entry_id, data in domain_data.items():
            # Check if this is a coordinator and if it matches the site
            if hasattr(data, 'site_name') and data.site_name == site.name:
                return data
        
        _LOGGER.warning(f"No coordinator found for site {site.name}")
    except Exception as e:
        _LOGGER.error(f"Error retrieving coordinator: {str(e)}")
    
    return None

def check_ha_connection(site):
    """
    Check if the Home Assistant WebSocket connection is active for this site.
    Returns boolean indicating connection status.
    """
    try:
        coordinator = get_site_coordinator(site)
        if coordinator and hasattr(coordinator, '_is_connected'):
            return coordinator._is_connected()
        return False
    except Exception as e:
        _LOGGER.error(f"Error checking connection status: {str(e)}")
        return False