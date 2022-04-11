from django.template import Library, Node
from django.template.defaulttags import token_kwargs

from ..context_processors import GlobalSettingProxy

register = Library()


class GetGlobalSettingNode(Node):
    def __init__(self, kwargs, target_var):
        self.kwargs = kwargs
        self.target_var = target_var

    @staticmethod
    def get_global_settings_object(context):
        if "request" in context:
            return GlobalSettingProxy(context["request"])

        raise RuntimeError("No request found in context")

    def render(self, context):
        resolved_kwargs = {k: v.resolve(context) for k, v in self.kwargs.items()}
        context[self.target_var] = self.get_global_settings_object(
            context, **resolved_kwargs
        )
        return ""


@register.tag
def get_global_settings(parser, token):
    bits = token.split_contents()[1:]
    target_var = "global_settings"
    if len(bits) >= 2 and bits[-2] == "as":
        target_var = bits[-1]
        bits = bits[:-2]
    kwargs = token_kwargs(bits, parser) if bits else {}
    return GetGlobalSettingNode(kwargs, target_var)
