"""
ASGI config for trust_project (used by async servers; optional for this MVP).
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trust_project.settings")

application = get_asgi_application()
