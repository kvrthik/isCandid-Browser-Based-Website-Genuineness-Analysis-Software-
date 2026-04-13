"""
URL routing for the whole Django project.
We expose API paths: /analyze/ and /health/
"""
from django.contrib import admin
from django.urls import path

# The analyze view lives in the analyzer app.
from analyzer import views

urlpatterns = [
    # Optional: Django admin (not required for the extension demo).
    path("admin/", admin.site.urls),
    # Main endpoint the browser extension calls with POST + JSON.
    path("analyze/", views.analyze, name="analyze"),
    # Simple deployment check endpoint.
    path("health/", views.health, name="health"),
]
