import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "planets_web.settings")

from planets_web.wsgi import application

# Vercel Python runtime looks for a top-level WSGI callable named `app`.
app = application
