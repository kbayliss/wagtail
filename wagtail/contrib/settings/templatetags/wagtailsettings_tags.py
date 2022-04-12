from django.template import Library, Node
from django.template.defaulttags import token_kwargs

from wagtail.models import Site

from ..context_processors import GenericSettingProxy, SiteSettingProxy

register = Library()


class AbstractSettingsNode(Node):
    def __init__(self, kwargs, target_var):
        self.kwargs = kwargs
        self.target_var = target_var

    def render(self, context):
        resolved_kwargs = {k: v.resolve(context) for k, v in self.kwargs.items()}
        context[self.target_var] = self.get_settings_object(context, **resolved_kwargs)
        return ""


class SiteSettingNode(AbstractSettingsNode):
    @staticmethod
    def get_settings_object(context, use_default_site=False):
        if use_default_site:
            site = Site.objects.get(is_default_site=True)
            return SiteSettingProxy(site)
        if "request" in context:
            return SiteSettingProxy(context["request"])

        raise RuntimeError(
            "No request found in context, and use_default_site flag not set"
        )


class GenericSettingNode(AbstractSettingsNode):
    @staticmethod
    def get_settings_object(context):
        if "request" in context:
            return GenericSettingProxy(context["request"])

        raise RuntimeError("No request found in context")


@register.tag
def get_site_settings(parser, token):
    bits = token.split_contents()[1:]
    target_var = "site_settings"
    if len(bits) >= 2 and bits[-2] == "as":
        target_var = bits[-1]
        bits = bits[:-2]
    kwargs = token_kwargs(bits, parser) if bits else {}
    return SiteSettingNode(kwargs, target_var)


@register.tag
def get_generic_settings(parser, token):
    bits = token.split_contents()[1:]
    target_var = "generic_settings"
    if len(bits) >= 2 and bits[-2] == "as":
        target_var = bits[-1]
        bits = bits[:-2]
    kwargs = token_kwargs(bits, parser) if bits else {}
    return GenericSettingNode(kwargs, target_var)
