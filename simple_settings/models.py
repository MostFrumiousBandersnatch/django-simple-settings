from django.conf import settings as _settings
from django.core.cache import get_cache
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

SIMPLE_SETTINGS_CACHE_TIMEOUT = getattr(_settings, 'SIMPLE_SETTINGS_CACHE_TIMEOUT', 60 * 60 * 24)
SIMPLE_SETTINGS_CACHE_ALIAS = getattr(_settings, 'SIMPLE_SETTINGS_CACHE_ALIAS', 'default')
SIMPLE_SETTINGS_CACHE_KEY = 'simple_settings:all'
cache = get_cache(SIMPLE_SETTINGS_CACHE_ALIAS)

def get_cache_item_key(key):
    return SIMPLE_SETTINGS_CACHE_KEY.replace('all', key)

class SettingsManager(models.Manager):
    def to_dict(self):
        result = {}
        for s in self.all():
            value = s.to_python()
            result[s.key] = value
            cache.set(get_cache_item_key(s.key), value)

        return result

    def get_item(self, key, default=None):
        """Returns setting ``value`` of ``key`` or ``default`` if ``key`` was not found."""
        cache_key = get_cache_item_key(key)
        value = cache.get(cache_key)

        if value is None:
            try:
                value = self.get(key=key).to_python()
            except Settings.DoesNotExist:
                value = default
            else:
                cache.set(cache_key, value)

        return value

    def set_item(self, key, value):
        """Sets setting ``key`` to ``value```"""
        value_type = type(value).__name__
        if value_type not in ('bool', 'float', 'int', 'str'):
            raise ValueError('Unsupported value type.')

        obj, created = self.get_or_create(key=key, defaults={'value': value, 'value_type': value_type})
        if not created:
            obj.key = key
            obj.value = value
            obj.value_type = value_type
            obj.save()

	    cache.set(get_cache_item_key(obj.key), obj.value)
        return obj

    def del_item(self, key):
        """Deletes setting ``key``"""
        try:
            self.get(key=key).delete()
        except self.model.DoesNotExist:
            raise KeyError(key)
	else:
	    cache.delete(get_cache_item_key(key))

    def clear_cache(self):
        """Clear cache of settings"""
        cache.delete(SIMPLE_SETTINGS_CACHE_KEY)


class Settings(models.Model):
    """Provides settings model"""
    VALUE_TYPE_CHOICES = (
        ('bool', _('Boolean')),
        ('float', _('Float')),
        ('int', _('Integer')),
        ('str', _('String')),
    )
    key = models.CharField(_('Key'), max_length=255, unique=True)
    value = models.CharField(_('Value'), max_length=255, default='', blank=True)
    value_type = models.CharField(_('Type'), max_length=10, choices=VALUE_TYPE_CHOICES,
                                  default=VALUE_TYPE_CHOICES[3][0], blank=True)

    objects = SettingsManager()

    class Meta:
        verbose_name = _('setting')
        verbose_name_plural = _('settings')

    def clean(self):
        if self.value_type == 'bool' and self.value not in ("true", "false"):
            raise ValidationError({'value': [_('For boolean type available case-insensitive values: true, false')]})
        elif self.value_type == 'float':
            try:
                float(self.value)
            except ValueError:
                raise ValidationError({'value': [_('Incorrect float value')]})
        elif self.value_type == 'int':
            try:
                int(self.value)
            except ValueError:
                raise ValidationError({'value': [_('Incorrect integer value')]})

    def to_python(self):
        if self.value_type == 'bool':
            result = True if self.value.lower() == "true" else False
        else:
            result = globals()['__builtins__'][self.value_type](self.value)

        return result


@receiver(signal=post_save, sender=Settings)
@receiver(signal=post_delete, sender=Settings)
def settings_update_handler(**kwargs):
    """Clear settings cache"""
    instance = kwargs.pop('instance')
    instance._default_manager.clear_cache()

