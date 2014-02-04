from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.client import Client

from simple_settings import settings

try:
    from django.test.utils import override_settings
except ImportError:  # for Django 1.3 support
    from django.conf import settings as project_settings

    def override_settings(**kw):
        def _override_settings(fn):
            def wrapped(*args, **kwargs):
                for key, value in kw.iteritems():
                    setattr(project_settings, key, value)
                return fn(*args, **kwargs)
            return wrapped
        return _override_settings


class SimpleSettingsTestCase(TestCase):
    def test_get_set(self):
        test_key = "test_get_key"
        test_value = "test_get_value"

        settings.set(test_key, test_value)
        self.assertEqual(settings.get(test_key), test_value)
        self.assertEqual(settings[test_key], test_value)

        test_key = "unknown_key"
        self.assertEqual(settings.get(test_key), None)
        try:
            self.assertEqual(settings[test_key], None)
        except KeyError:
            pass
        else:
            pass
            #self.fail("Should throw KeyError exception")

        self.assertEqual(settings.get(test_key, default=666), 666)

    def test_set_override(self):
        test_key = "test_set_override_key"

        settings.set(test_key, "test_value_1")
        settings.set(test_key, "test_value_2")
        self.assertEqual(settings.get(test_key), "test_value_2")

    def test_delete(self):
        test_key = "test_delete_key"
        test_value = "test_delete_value"

        settings.set(test_key, test_value)
        settings.delete(test_key)
        self.assertEqual(settings.get(test_key), None)

        # test delete unexisted setting
        try:
            settings.delete(test_key)
        except KeyError:
            pass
        else:
            self.fail("Should throw KeyError exception")

    def test_boolean_key(self):
        test_key = "test_boolean_key"

        # test true
        settings.set(test_key, True)
        self.assertEqual(settings.get(test_key), True)

        # test false
        settings.set(test_key, False)
        self.assertEqual(settings.get(test_key), False)

    def test_integer_key(self):
        test_key = "test_integer_key"

        settings.set(test_key, 666)
        self.assertEqual(settings.get(test_key), 666)

    def test_float_key(self):
        test_key = "test_float_key"

        settings.set(test_key, 0.666)
        self.assertEqual(settings.get(test_key), 0.666)

    @override_settings(DEBUG=True)
    def test_cache(self):
        test_key = "test_cache_key"
        test_value = "test_cache_vaue"

        settings.set(test_key, test_value)
        self.assertEqual(settings.get(test_key), test_value)

        count_queries = len(connection.queries)
        self.assertNotEqual(count_queries, 0)

        for x in range(10):
            self.assertEqual(settings.get(test_key + str(x)), None)

        # Count queries should not be changed
        #self.assertEqual(count_queries, len(connection.queries))

    def test_cache_invalidation(self):
        test_key = "test_cache_invalidation_key"
        test_value = "test_cache_invalidation_value"

        settings.set(test_key, test_value)
        self.assertEqual(settings.get(test_key), test_value)

        # Test invalidation on update
        settings.set(test_key, "new_test_value")
        self.assertEqual(settings.get(test_key), "new_test_value")

        # Test invalidation on delete
        settings.delete(test_key)
        self.assertEqual(settings.get(test_key), None)

    def test_context_processors(self):
        test_key = "test_setting_key"
        test_value = "test_setting_value"

        settings.set(test_key, test_value)
        c = Client()
        response = c.get('/test_context_processor/')
        self.assertContains(response, test_value)

        settings.set(test_key, "test_setting_value_2")
        c = Client()
        response = c.get('/test_context_processor/')
        self.assertContains(response, "test_setting_value_2")

        settings.delete(test_key)
        c = Client()
        response = c.get('/test_context_processor/')
        self.assertNotContains(response, test_value)

    def test_unknown_attribute(self):
        try:
            settings.foo('bar')
        except AttributeError:
            pass
        else:
            self.fail("Should throw AttributeError exception")

    def test_unsupported_type(self):
        try:
            settings.set('test_key', {'1': '1'})
        except ValueError:
            pass
        else:
            self.fail("Should throw ValueError exception")

    def test_clean_model_settings(self):
        from simple_settings.models import Settings
        obj = Settings(key='test_clean_model_settings_key', value='test_value')
        obj.clean()

        for vtype in ('bool', 'float', 'int'):
            obj.value = vtype
            obj.value_type = vtype
            try:
                obj.clean()
            except ValidationError:
                pass
            else:
                self.fail("Should throw ValidationError exception. Trace: vtype=%s" % vtype)
