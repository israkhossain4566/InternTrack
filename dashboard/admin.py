from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'is_read', 'created_at', 'short_message')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__username', 'message')
    ordering = ('-created_at',)

    def short_message(self, obj):
        return obj.message[:80]
    short_message.short_description = 'Message'
