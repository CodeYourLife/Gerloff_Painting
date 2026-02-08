import os
import sys

# ADD THIS LINE — project root
sys.path.append(r"D:\Gerloff_Painting")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trinity.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()