"""Passenger WSGI entrypoint for cPanel / CloudLinux.

Configure the Python interpreter and application root in cPanel Application
Manager (or Passenger* directives). See docs/PASSENGER_DEPLOYMENT.md.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zarrah_foundation.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()