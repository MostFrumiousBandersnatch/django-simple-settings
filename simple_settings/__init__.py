from .models import Settings
from django.conf import settings as static_settings

VERSION = '0.3.1'


class LazySettings(object):
    """Provides lazy settings"""
    _interface = {
        'get': 'get_item',
        'set': 'set_item',
        'delete': 'del_item',
        'all': 'to_dict'
    }

    def __getattr__(self, item):
        if item in self._interface:
            return getattr(Settings.objects, self._interface[item])
        else:
            data = Settings.objects.get_item(item)
            if data is not None:
                return data
            else:
                return getattr(static_settings, item)

    def __getitem__(self, item):
        return Settings.objects.get_item(item)

settings = LazySettings()

