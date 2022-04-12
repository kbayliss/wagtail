import warnings

from django.db import models

from wagtail.coreutils import InvokeViaAttributeShortcut
from wagtail.models import Site
from wagtail.utils.deprecation import RemovedInWagtail50Warning

from .registry import register_setting

__all__ = [
    "BaseSiteSetting",
    "BaseSetting",  # Deprecated
    "BaseGenericSetting",
    "register_setting",
]


class AbstractSetting(models.Model):
    """
    The abstract base model for settings. Subclasses must be registered using
    :func:`~wagtail.contrib.settings.registry.register_setting`
    """

    class Meta:
        abstract = True

    # Override to fetch ForeignKey values in the same query when
    # retrieving settings (e.g. via `for_request()`)
    select_related = None
    is_sites_aware: bool = False

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
    def for_request(cls, request):
        """
        Get or create an instance of this model for the request,
        and cache the result on the request for faster repeat access.
        """
        attr_name = cls.get_cache_attr_name()
        if hasattr(request, attr_name):
            return getattr(request, attr_name)
        site = Site.find_for_request(request)
        site_settings = cls.for_site(site)
        # to allow more efficient page url generation
        site_settings._request = request
        setattr(request, attr_name, site_settings)
        return site_settings

    @classmethod
    def get_cache_attr_name(cls):
        """
        Returns the name of the attribute that should be used to store
        a reference to the fetched/created object on a request.
        """
        return "_{}.{}".format(cls._meta.app_label, cls._meta.model_name).lower()

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
            url = page.specific.get_url(getattr(self, "_request", None))
        else:
            url = ""

        self._page_url_cache[attribute_name] = url
        return url


class BaseSiteSetting(AbstractSetting):
    site = models.OneToOneField(
        Site, unique=True, db_index=True, editable=False, on_delete=models.CASCADE
    )

    class Meta:
        abstract = True

    is_sites_aware: bool = True

    @classmethod
    def for_site(cls, site):
        """
        Get or create an instance of this setting for the site.
        """
        queryset = cls.base_queryset()
        instance, created = queryset.get_or_create(site=site)
        return instance

    def __str__(self):
        return "%s for %s" % (self._meta.verbose_name.capitalize(), self.site)


class BaseGenericSetting(AbstractSetting):
    class Meta:
        abstract = True

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

    def __str__(self):
        return self._meta.verbose_name.capitalize()


class BaseSetting(BaseSiteSetting):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            (
                "wagtail.contrib.settings.models.BaseSetting "
                "is obsolete and should be replaced by "
                "wagtail.contrib.settings.models.BaseSiteSetting"
            ),
            category=RemovedInWagtail50Warning,
            stacklevel=2,
        )
        return super().__init__(self, *args, **kwargs)
