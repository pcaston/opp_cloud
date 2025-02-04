import sys, os

# Add the directory containing your Django project to the Python path
sys.path.append('/openpeerpower/opp_cloud')

# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ['DJANGO_SETTINGS_MODULE'] = 'opp_cloud.settings'

# Create a WSGI application object
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
