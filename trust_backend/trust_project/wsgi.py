"""
WSGI config for trust_project (used when deploying with gunicorn/waitress, etc.).
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trust_project.settings")

application = get_wsgi_application()
