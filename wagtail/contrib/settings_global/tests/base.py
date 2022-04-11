from django.http import HttpRequest

from wagtail.models import Page, Site
from wagtail.test.testapp.models import TestGlobalSetting


class GlobalSettingsTestMixin:
    def setUp(self):
        self.default_site = Site.objects.get(is_default_site=True)
        self.root_page = self.default_site.root_page
        self.other_root_page = Page(title="Other Root")
        self.default_global_settings = TestGlobalSetting.objects.create(
            title="Default GlobalSettings title", email="email@example.com"
        )

        self.default_site.root_page.add_child(instance=self.other_root_page)

    def get_request(self):
        request = HttpRequest()
        request.META["HTTP_HOST"] = self.default_site.hostname
        request.META["SERVER_PORT"] = self.default_site.port
        return request
