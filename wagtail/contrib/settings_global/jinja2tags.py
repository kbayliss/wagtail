from weakref import WeakKeyDictionary

import jinja2
from django.http import HttpRequest
from django.utils.encoding import force_str
from jinja2.ext import Extension

from wagtail.contrib.settings_global.registry import registry

# Settings are cached per template context, to prevent excessive database
# lookups. The cached settings are disposed of once the template context is no
# longer used.
global_settings_cache = WeakKeyDictionary()


class GlobalSettingsContextCache(dict):
    """
    A cache of global settings for a template Context
    """

    def __missing__(self, key):
        """
        Make a GlobalSetting for the request
        """
        if not (isinstance(key, HttpRequest)):
            raise TypeError
        out = self[key] = GlobalSetting(key)
        return out


class GlobalSetting(dict):
    """
    A cache of settings
    """

    def __init__(self, request):
        super().__init__()
        self.request = request

    def __getitem__(self, key):
        # Normalise all keys to lowercase
        return super().__getitem__(force_str(key).lower())

    def __missing__(self, key):
        """
        Get the settings instance, and store it for later
        """
        try:
            app_label, model_name = key.split(".", 1)
        except ValueError:
            raise KeyError("Invalid model name: {}".format(key))
        Model = registry.get_by_natural_key(app_label, model_name)
        if Model is None:
            raise KeyError("Unknown setting: {}".format(key))

        out = self[key] = Model.for_request(request=self.request)
        return out


@jinja2.pass_context
def get_global_setting(context, model_string):
    if "request" in context:
        request = context["request"]
    else:
        raise RuntimeError("No request found in context")

    # Sadly, WeakKeyDictionary can not implement __missing__, so we have to do
    # this one manually
    try:
        context_cache = global_settings_cache[context]
    except KeyError:
        context_cache = global_settings_cache[context] = GlobalSettingsContextCache()
    # These ones all implement __missing__ in a useful way though
    return context_cache[request][model_string]


class GlobalSettingsExtension(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        self.environment.globals.update(
            {
                "global_settings": get_global_setting,
            }
        )


global_settings = GlobalSettingsExtension
