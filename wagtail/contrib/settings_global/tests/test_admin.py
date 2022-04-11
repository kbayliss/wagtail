from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils.text import capfirst

from wagtail import hooks
from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.admin.panels import FieldPanel, ObjectList, TabbedInterface
from wagtail.contrib.settings_global.registry import GlobalSettingMenuItem
from wagtail.contrib.settings_global.views import get_global_setting_edit_handler
from wagtail.test.testapp.models import (
    FileGlobalSetting,
    IconGlobalSetting,
    PanelGlobalSettings,
    TabbedGlobalSettings,
    TestGlobalSetting,
)
from wagtail.test.utils import WagtailTestUtils


class TestGlobalSettingMenu(TestCase, WagtailTestUtils):
    def login_only_admin(self):
        """Log in with a user that only has permission to access the admin"""
        user = self.create_user(username="test", password="password")
        user.user_permissions.add(
            Permission.objects.get_by_natural_key(
                codename="access_admin", app_label="wagtailadmin", model="admin"
            )
        )
        self.login(username="test", password="password")
        return user

    def test_menu_item_in_admin(self):
        self.login()
        response = self.client.get(reverse("wagtailadmin_home"))

        self.assertContains(response, capfirst(TestGlobalSetting._meta.verbose_name))
        self.assertContains(
            response,
            reverse("wagtailglobalsettings:edit", args=("tests", "testglobalsetting")),
        )

    def test_menu_item_no_permissions(self):
        self.login_only_admin()
        response = self.client.get(reverse("wagtailadmin_home"))

        self.assertNotContains(response, TestGlobalSetting._meta.verbose_name)
        self.assertNotContains(
            response,
            reverse("wagtailglobalsettings:edit", args=("tests", "testglobalsetting")),
        )

    def test_menu_item_icon(self):
        menu_item = GlobalSettingMenuItem(
            IconGlobalSetting, icon="tag", classnames="test-class"
        )
        self.assertEqual(menu_item.icon_name, "tag")
        self.assertEqual(menu_item.classnames, "test-class")

    def test_menu_item_icon_fontawesome(self):
        menu_item = GlobalSettingMenuItem(
            IconGlobalSetting, icon="fa-suitcase", classnames="test-class"
        )
        self.assertEqual(menu_item.icon_name, "")
        self.assertEqual(
            set(menu_item.classnames.split(" ")),
            {"icon", "icon-fa-suitcase", "test-class"},
        )


class BaseTestGlobalSettingView(TestCase, WagtailTestUtils):
    def get(self, pk=1, params={}, setting=TestGlobalSetting):
        url = self.edit_url(setting=setting, pk=pk)
        return self.client.get(url, params)

    def post(self, pk=1, post_data={}, setting=TestGlobalSetting):
        url = self.edit_url(setting=setting, pk=pk)
        return self.client.post(url, post_data)

    def edit_url(self, setting, pk=1):
        args = [setting._meta.app_label, setting._meta.model_name, pk]
        return reverse("wagtailglobalsettings:edit", args=args)


class TestGlobalSettingCreateView(BaseTestGlobalSettingView):
    def setUp(self):
        self.user = self.login()

    def test_get_edit(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)

    def test_edit_invalid(self):
        response = self.post(post_data={"foo": "bar"})
        self.assertContains(response, "The setting could not be saved due to errors.")
        self.assertContains(
            response,
            """<p class="error-message"><span>This field is required.</span></p>""",
            count=2,
            html=True,
        )
        self.assertContains(response, "This field is required", count=2)

    def test_edit(self):
        response = self.post(
            post_data={
                "title": "Edited setting title",
                "email": "edited.email@example.com",
            }
        )
        self.assertEqual(response.status_code, 302)

        setting = TestGlobalSetting.objects.first()
        self.assertEqual(setting.title, "Edited setting title")

        url_finder = AdminURLFinder(self.user)
        expected_url = "/admin/global-settings/tests/testglobalsetting/%d/" % setting.pk
        self.assertEqual(url_finder.get_edit_url(setting), expected_url)

    def test_file_upload_multipart(self):
        response = self.get(setting=FileGlobalSetting)
        # Ensure the form supports file uploads
        self.assertContains(response, 'enctype="multipart/form-data"')


class TestGlobalSettingEditView(BaseTestGlobalSettingView):
    def setUp(self):
        self.test_setting = TestGlobalSetting()
        self.test_setting.title = "Setting title"
        self.test_setting.save()

        self.login()

    def test_get_edit(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)

    def test_non_existent_model(self):
        response = self.client.get(
            reverse("wagtailglobalsettings:edit", args=["test", "foo", 1])
        )
        self.assertEqual(response.status_code, 404)

    def test_edit_invalid(self):
        response = self.post(post_data={"foo": "bar"})
        self.assertContains(response, "The setting could not be saved due to errors.")
        self.assertContains(
            response,
            """<p class="error-message"><span>This field is required.</span></p>""",
            count=2,
            html=True,
        )
        self.assertContains(response, "This field is required", count=2)

    def test_edit(self):
        response = self.post(
            post_data={
                "title": "Edited setting title",
                "email": "different.email@example.com",
            }
        )
        self.assertEqual(response.status_code, 302)

        setting = TestGlobalSetting.objects.first()
        self.assertEqual(setting.title, "Edited setting title")

    def test_for_request(self):
        url = reverse("wagtailglobalsettings:edit", args=("tests", "testglobalsetting"))

        response = self.client.get(url)
        self.assertRedirects(
            response,
            status_code=302,
            expected_url="%s%s/" % (url, TestGlobalSetting.objects.first().pk),
        )

    def test_for_request_deleted(self):
        TestGlobalSetting.objects.all().delete()

        url = reverse("wagtailglobalsettings:edit", args=("tests", "testglobalsetting"))

        response = self.client.get(url)
        self.assertRedirects(
            response,
            status_code=302,
            expected_url="%s%s/" % (url, TestGlobalSetting.objects.first().pk),
        )


class TestAdminPermission(TestCase, WagtailTestUtils):
    def test_registered_permission(self):
        permission = Permission.objects.get_by_natural_key(
            app_label="tests",
            model="testglobalsetting",
            codename="change_testglobalsetting",
        )
        for fn in hooks.get_hooks("register_permissions"):
            if permission in fn():
                break
        else:
            self.fail("Change permission for tests.TestGlobalSetting not registered")


class TestEditHandlers(TestCase):
    def setUp(self):
        get_global_setting_edit_handler.cache_clear()

    def test_default_model_introspection(self):
        handler = get_global_setting_edit_handler(TestGlobalSetting)
        self.assertIsInstance(handler, ObjectList)
        self.assertEqual(len(handler.children), 2)
        first = handler.children[0]
        self.assertIsInstance(first, FieldPanel)
        self.assertEqual(first.field_name, "title")
        second = handler.children[1]
        self.assertIsInstance(second, FieldPanel)
        self.assertEqual(second.field_name, "email")

    def test_with_custom_panels(self):
        handler = get_global_setting_edit_handler(PanelGlobalSettings)
        self.assertIsInstance(handler, ObjectList)
        self.assertEqual(len(handler.children), 1)
        first = handler.children[0]
        self.assertIsInstance(first, FieldPanel)
        self.assertEqual(first.field_name, "title")

    def test_with_custom_edit_handler(self):
        handler = get_global_setting_edit_handler(TabbedGlobalSettings)
        self.assertIsInstance(handler, TabbedInterface)
        self.assertEqual(len(handler.children), 2)
