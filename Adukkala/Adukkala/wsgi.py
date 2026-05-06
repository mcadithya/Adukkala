"""
WSGI config for Adukkala project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Adukkala.settings')

application = get_wsgi_application()
