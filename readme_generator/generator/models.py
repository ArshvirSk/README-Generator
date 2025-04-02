# generator/models.py
from django.db import models


class Repository(models.Model):
    repo_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
