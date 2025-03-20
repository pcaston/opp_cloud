from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from .models import Site, EnergyPrice  # Updated import
from django.shortcuts import render, get_object_or_404
from datetime import datetime

def home(request):
    return render(request, 'core/home.html')

@csrf_exempt
def wstest(request):
    return render(request, 'core/wstest.html')

@csrf_exempt
@login_required
def register_instance(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        
        # Check if a site with this name already exists for the user
        site, created = Site.objects.get_or_create(
            user=request.user,
            name=data['name'],
            defaults={
                'instance_id': data.get('instance_id'),
                'ws_connected': False,
                'last_connected': None
            }
        )
        
        # If the site already existed but needs to update instance_id
        if not created and data.get('instance_id') and site.instance_id != data.get('instance_id'):
            site.instance_id = data.get('instance_id')
            site.save()
            
        return JsonResponse({'status': 'success', 'site_id': site.id, 'instance_id': site.instance_id})
    return JsonResponse({'status': 'error'}, status=405)

@csrf_exempt
@login_required
def update_price(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            # Create energy price record - no relation to site
            price = EnergyPrice.objects.create(
                buy_price=data.get('buy_price'),
                sell_price=data.get('sell_price'),
                valid_until=data.get('valid_until')
            )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({'status': 'error'}, status=405)

# New view to check site connection status
@login_required
def site_status(request, site_id):
    site = get_object_or_404(Site, id=site_id, user=request.user)
    
    return JsonResponse({
        'id': site.id,
        'name': site.name,
        'instance_id': site.instance_id,
        'connected': site.ws_connected,
        'last_connected': site.last_connected.isoformat() if site.last_connected else None
    })