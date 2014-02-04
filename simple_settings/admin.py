from django.contrib import admin
from django.core.cache import get_cache

from .models import (Settings, cache, get_cache_item_key)

class SettingsAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'value_type']
    search_fields = ['key', 'value']

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        obj.save()
        cache.delete(get_cache_item_key(obj.key))

admin.site.register(Settings, SettingsAdmin)

