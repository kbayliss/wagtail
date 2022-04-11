from django.test import TestCase
from django.urls import reverse

from wagtail.contrib.settings_global.registry import GlobalSettingRegistry
from wagtail.test.testapp.models import NotYetRegisteredGlobalSetting
from wagtail.test.utils import WagtailTestUtils


class GlobalSettingRegisterTestCase(TestCase, WagtailTestUtils):
    def setUp(self):
        self.registry = GlobalSettingRegistry()
        self.login()

    def test_register(self):
        self.assertNotIn(NotYetRegisteredGlobalSetting, self.registry)
        NowRegisteredGlobalSetting = self.registry.register_decorator(
            NotYetRegisteredGlobalSetting
        )
        self.assertIn(NotYetRegisteredGlobalSetting, self.registry)
        self.assertIs(NowRegisteredGlobalSetting, NotYetRegisteredGlobalSetting)

    def test_icon(self):
        admin = self.client.get(reverse("wagtailadmin_home"))
        self.assertContains(admin, "icon-setting-tag")
