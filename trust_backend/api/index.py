"""
Vercel serverless entrypoint for Django.
"""
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trust_project.settings")

from trust_project.wsgi import application  # noqa: E402

app = application

