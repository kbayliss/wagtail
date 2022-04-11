from django.utils.functional import SimpleLazyObject

from .registry import registry


class GlobalSettingProxy(dict):
    """
    Get a GlobalSettingModuleProxy for an app using proxy['app_label']
    """

    def __init__(self, request):
        self.request = request

    def __missing__(self, app_label):
        self[app_label] = value = GlobalSettingModuleProxy(self.request, app_label)
        return value

    def __str__(self):
        return "GlobalSettingProxy"


class GlobalSettingModuleProxy(dict):
    """
    Get a setting instance using proxy['modelname']
    """

    def __init__(self, request, app_label):
        self.request = request
        self.app_label = app_label

    def __getitem__(self, model_name):
        """Get a setting instance for a model"""
        # Model names are treated as case-insensitive
        return super().__getitem__(model_name.lower())

    def __missing__(self, model_name):
        """Get and cache settings that have not been looked up yet"""
        self[model_name] = value = self.get_global_setting(model_name)
        return value

    def get_global_setting(self, model_name):
        """
        Get a setting instance
        """
        Model = registry.get_by_natural_key(self.app_label, model_name)
        if Model is None:
            return None

        return Model.for_request(request=self.request)

    def __str__(self):
        return "GlobalSettingModuleProxy({0})".format(self.app_label)


def global_settings(request):
    # delay query until settings values are needed
    def _inner(request):
        return GlobalSettingProxy(request)

    return {"global_settings": SimpleLazyObject(lambda: _inner(request))}
