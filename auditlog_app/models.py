from django.conf import settings
from django.db import models

class ActivityEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=24)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    status_code = models.PositiveSmallIntegerField(default=200)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', '-created_at'])]
    def __str__(self):
        return f'{self.action}: {self.path}'
