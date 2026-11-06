from django.contrib import admin
from .models import ActivityEvent
@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'method', 'path', 'status_code', 'ip_address')
    list_filter = ('action', 'method', 'status_code')
    search_fields = ('user__username', 'path', 'ip_address')
    readonly_fields = [f.name for f in ActivityEvent._meta.fields]
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
