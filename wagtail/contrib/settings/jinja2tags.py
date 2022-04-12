from weakref import WeakKeyDictionary

import jinja2
from django.http import HttpRequest
from django.utils.encoding import force_str
from jinja2.ext import Extension

from wagtail.contrib.settings.registry import registry
from wagtail.models import Site

# Settings are cached per template context, to prevent excessive database
# lookups. The cached settings are disposed of once the template context is no
# longer used.
site_settings_cache = WeakKeyDictionary()
generic_settings_cache = WeakKeyDictionary()


class SiteSettingContextCache(dict):
    """
    A cache of Sites and their Settings for a template Context
    """

    def __missing__(self, key):
        """
        Make a SiteSetting for a new Site
        """
        if not (isinstance(key, Site)):
            raise TypeError
        out = self[key] = SiteSetting(key)
        return out


class GenericSettingContextCache(dict):
    """
    A cache of global settings for a template Context
    """

    def __missing__(self, key):
        """
        Make a GenericSetting for the request
        """
        if not (isinstance(key, HttpRequest)):
            raise TypeError
        out = self[key] = GenericSetting(key)
        return out


class AbstractSetting(dict):
    """
    A cache of Settings for a specific Site
    """

    def __getitem__(self, key):
        # Normalise all keys to lowercase
        return super().__getitem__(force_str(key).lower())

    def __missing__(self, key):
        """
        Get the settings instance for this site, and store it for later
        """
        try:
            app_label, model_name = key.split(".", 1)
        except ValueError:
            raise KeyError("Invalid model name: {}".format(key))
        Model = registry.get_by_natural_key(app_label, model_name)
        if Model is None:
            raise KeyError("Unknown setting: {}".format(key))

        if Model.is_sites_aware:
            out = self[key] = Model.for_site(self.site)
        else:
            out = self[key] = Model.for_request(request=self.request)

        return out


class SiteSetting(AbstractSetting):
    """
    A cache of Settings for a specific Site
    """

    def __init__(self, site):
        super().__init__()
        self.site = site


class GenericSetting(AbstractSetting):
    """
    A cache of generic Settings for across all sites.
    """

    def __init__(self, request):
        super().__init__()
        self.request = request


@jinja2.pass_context
def get_site_setting(context, model_string, use_default_site=False):
    if use_default_site:
        site = Site.objects.get(is_default_site=True)
    elif "request" in context:
        site = Site.find_for_request(context["request"])
    else:
        raise RuntimeError(
            "No request found in context, and use_default_site " "flag not set"
        )

    # Sadly, WeakKeyDictionary can not implement __missing__, so we have to do
    # this one manually
    try:
        context_cache = site_settings_cache[context]
    except KeyError:
        context_cache = site_settings_cache[context] = SiteSettingContextCache()
    # These ones all implement __missing__ in a useful way though
    return context_cache[site][model_string]


@jinja2.pass_context
def get_generic_setting(context, model_string):
    if "request" in context:
        request = context["request"]
    else:
        raise RuntimeError("No request found in context")

    # Sadly, WeakKeyDictionary can not implement __missing__, so we have to do
    # this one manually
    try:
        context_cache = generic_settings_cache[context]
    except KeyError:
        context_cache = generic_settings_cache[context] = GenericSettingContextCache()
    # These ones all implement __missing__ in a useful way though
    return context_cache[request][model_string]


class SiteSettingsExtension(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        self.environment.globals.update(
            {
                "site_settings": get_site_setting,
            }
        )


site_settings = SiteSettingsExtension


class GenericSettingsExtension(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        self.environment.globals.update(
            {
                "generic_settings": get_generic_setting,
            }
        )


generic_settings = GenericSettingsExtension
