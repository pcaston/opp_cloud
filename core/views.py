from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from .models import HomeAssistantInstance, EnergyPrice

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