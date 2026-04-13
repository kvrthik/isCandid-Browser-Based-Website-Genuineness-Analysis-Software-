"""
Database models for the analyzer app.
"""
from django.db import models


class WebsiteCache(models.Model):
    """
    Stores analyzed website results for local DB-backed caching.
    """
    url_key = models.TextField(primary_key=True)
    url = models.TextField()
    website_name = models.TextField(blank=True, null=True)
    trust_score = models.IntegerField(blank=True, null=True)
    risk_level = models.TextField(blank=True, null=True)
    confidence_level = models.TextField(blank=True, null=True)
    analysis_json = models.JSONField()
    access_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField()
    last_accessed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "website_cache"
