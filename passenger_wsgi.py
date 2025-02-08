import os
import sys

# Add project path
sys.path.append('/home/senasnau/openpeerpower.net')  # Make sure Django can find the project

# Set the correct settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'opp_cloud.settings')

# Load Django WSGI application (for HTTP requests)
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
