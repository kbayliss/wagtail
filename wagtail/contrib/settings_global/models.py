from django.db import models

from wagtail.coreutils import InvokeViaAttributeShortcut

from .registry import register_global_setting

__all__ = ["BaseGlobalSetting", "register_global_setting"]


class BaseGlobalSetting(models.Model):
    """
    The abstract base model for global settings. Subclasses must be registered using
    :func:`~wagtail.contrib.settings_global.registry.register_global_setting`
    """

    select_related = None

    class Meta:
        abstract = True

    @classmethod
    def base_queryset(cls):
        """
        Returns a queryset of objects of this type to use as a base
        for calling get_or_create() on.

        You can use the `select_related` attribute on your class to
        specify a list of foreign key field names, which the method
        will attempt to select additional related-object data for
        when the query is executed.

        If your needs are more complex than this, you can override
        this method on your custom class.
        """
        queryset = cls.objects.all()
        if cls.select_related is not None:
            queryset = queryset.select_related(*cls.select_related)
        return queryset

    @classmethod
    def get_cache_attr_name(cls):
        """
        Returns the name of the attribute that should be used to store
        a reference to the fetched/created object on a request.
        """
        return "_{}.{}".format(cls._meta.app_label, cls._meta.model_name).lower()

    @classmethod
    def for_request(cls, request):
        """
        Get or create an instance of this model for the request,
        and cache the result on the request for faster repeat access.
        """
        attr_name = cls.get_cache_attr_name()
        if hasattr(request, attr_name):
            return getattr(request, attr_name)

        # Try to get first instance of this model.
        instance = cls.base_queryset().first()
        if instance is None:
            # Instance doesn't exist yet - create it.
            instance = cls.base_queryset().create()

        # Stash request for later (see `get_page_url`)
        instance._request = request

        # Cache instance to avoid subsequent queries for this request.
        setattr(request, attr_name, instance)
        return instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allows get_page_url() to be invoked using
        # `obj.page_url.foreign_key_name` syntax
        self.page_url = InvokeViaAttributeShortcut(self, "get_page_url")
        # Per-instance page URL cache
        self._page_url_cache = {}

    def get_page_url(self, attribute_name, request=None):
        """
        Returns the URL of a page referenced by a foreign key
        (or other attribute) matching the name ``attribute_name``.
        If the field value is null, or links to something other
        than a ``Page`` object, an empty string is returned.
        The result is also cached per-object to facilitate
        fast repeat access.

        Raises an ``AttributeError`` if the object has no such
        field or attribute.
        """
        if attribute_name in self._page_url_cache:
            return self._page_url_cache[attribute_name]

        if not hasattr(self, attribute_name):
            raise AttributeError(
                "'{}' object has no attribute '{}'".format(
                    self.__class__.__name__, attribute_name
                )
            )

        page = getattr(self, attribute_name)

        if hasattr(page, "specific"):
            url = page.specific.get_url(request=getattr(self, "_request", None))
        else:
            url = ""

        self._page_url_cache[attribute_name] = url
        return url
