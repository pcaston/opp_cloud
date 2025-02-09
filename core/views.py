from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from .models import HomeAssistantInstance, EnergyPrice
from django.shortcuts import render

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
        instance = HomeAssistantInstance.objects.create(
            user=request.user,
            instance_id=data['instance_id'],
            name=data['name'],
            api_token=data['api_token']
        )
        return JsonResponse({'status': 'success', 'instance_id': instance.instance_id})
    return JsonResponse({'status': 'error'}, status=405)

@csrf_exempt
@login_required
def update_price(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            instance = HomeAssistantInstance.objects.get(
                instance_id=data['instance_id'],
                user=request.user
            )
            price = EnergyPrice.objects.create(
                instance=instance,
                price=data['price'],
                valid_until=data['valid_until']
            )
            return JsonResponse({'status': 'success'})
        except HomeAssistantInstance.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Instance not found'
            }, status=404)
    return JsonResponse({'status': 'error'}, status=405)