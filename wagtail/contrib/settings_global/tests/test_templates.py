from django.http import HttpRequest
from django.template import Context, RequestContext, Template, engines
from django.test import TestCase
from django.test.utils import override_settings

from wagtail.models import Site
from wagtail.test.utils import WagtailTestUtils

from .base import GlobalSettingsTestMixin


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "other"])
class GlobalSettingTemplateTestCase(
    GlobalSettingsTestMixin, TestCase, WagtailTestUtils
):
    def render(self, request, string, context=None):
        template = Template(string)
        context = RequestContext(request, context)
        return template.render(context)


class GlobalSettingContextProcessorTestCase(GlobalSettingTemplateTestCase):
    def test_accessing_setting(self):
        """Check that the context processor works"""
        request = self.get_request()
        self.assertEqual(
            self.render(request, "{{ global_settings.tests.TestGlobalSetting.title }}"),
            self.default_global_settings.title,
        )

    def test_model_case_insensitive(self):
        """Model names should be case insensitive"""
        request = self.get_request()
        self.assertEqual(
            self.render(request, "{{ global_settings.tests.testglobalsetting.title }}"),
            self.default_global_settings.title,
        )
        self.assertEqual(
            self.render(request, "{{ global_settings.tests.TESTGLOBALSETTING.title }}"),
            self.default_global_settings.title,
        )
        self.assertEqual(
            self.render(request, "{{ global_settings.tests.TestGlobalSetting.title }}"),
            self.default_global_settings.title,
        )
        self.assertEqual(
            self.render(request, "{{ global_settings.tests.tEstgLobALsEttIng.title }}"),
            self.default_global_settings.title,
        )

    def test_models_cached(self):
        """Accessing a setting should only hit the DB once per request instance,
        even if using that request to rendering multiple times"""
        request = self.get_request()
        get_title = "{{ global_settings.tests.testglobalsetting.title }}"

        with self.assertNumQueries(1):
            for i in range(1, 4):
                with self.subTest(attempt=i):
                    self.assertEqual(
                        self.render(request, get_title * i),
                        self.default_global_settings.title * i,
                    )


class GlobalSettingTemplateTagTestCase(GlobalSettingTemplateTestCase):
    def test_no_context_processor(self):
        """
        Assert that not running the context processor means settings are not in
        the context, as expected.
        """
        template = Template("{{ global_settings.tests.TestGlobalSetting.title }}")
        context = Context()
        self.assertEqual(template.render(context), "")

    def test_get_global_settings_request_context(self):
        """Check that the {% get_global_settings %} tag works"""
        request = self.get_request()
        context = Context({"request": request})

        template = Template(
            "{% load wagtailglobalsettings_tags %}"
            "{% get_global_settings %}"
            "{{ global_settings.tests.testglobalsetting.title }}"
        )

        self.assertEqual(template.render(context), self.default_global_settings.title)

    def test_get_global_settings_no_request(self):
        """Check that the {% get_global_settings %} tag works with no request"""
        context = Context()

        template = Template(
            "{% load wagtailglobalsettings_tags %}"
            "{% get_global_settings %}"
            "{{ global_settings.tests.testglobalsetting.title }}"
        )
        with self.assertRaises(RuntimeError):
            template.render(context)

    def test_get_global_settings_variable_assignment_request_context(self):
        """
        Check that assigning the setting to a context variable with
        {% get_global_settings as wagtail_settings %} works.
        """
        request = self.get_request()
        context = Context({"request": request})
        template = Template(
            "{% load wagtailglobalsettings_tags %}"
            "{% get_global_settings as wagtail_settings %}"
            "{{ wagtail_settings.tests.testglobalsetting.title }}"
        )
        self.assertEqual(template.render(context), self.default_global_settings.title)

        # Also check that the default 'global_settings' variable hasn't been set
        template = Template(
            "{% load wagtailglobalsettings_tags %}"
            "{% get_global_settings as wagtail_settings %}"
            "{{ global_settings.tests.testglobalsetting.title }}"
        )
        self.assertEqual(template.render(context), "")


class GlobalSettingJinjaContextProcessorTestCase(GlobalSettingTemplateTestCase):
    def setUp(self):
        super().setUp()
        self.engine = engines["jinja2"]

    def render(self, string, context=None, request_context=True):
        if context is None:
            context = {}

        # Add a request to the template, to simulate a RequestContext
        if request_context:
            site = Site.objects.get(is_default_site=True)
            request = HttpRequest()
            request.META["HTTP_HOST"] = site.hostname
            request.META["SERVER_PORT"] = site.port
            context["request"] = request

        template = self.engine.from_string(string)
        return template.render(context)

    def test_accessing_setting(self):
        """Check that the context processor works"""
        self.assertEqual(
            self.render('{{ global_settings("tests.TestGlobalSetting").title }}'),
            self.default_global_settings.title,
        )

    def test_model_case_insensitive(self):
        """Model names should be case insensitive"""
        self.assertEqual(
            self.render('{{ global_settings("tests.testglobalsetting").title }}'),
            self.default_global_settings.title,
        )
        self.assertEqual(
            self.render('{{ global_settings("tests.TESTGLOBALSETTING").title }}'),
            self.default_global_settings.title,
        )
        self.assertEqual(
            self.render('{{ global_settings("tests.TestGlobalSetting").title }}'),
            self.default_global_settings.title,
        )
        self.assertEqual(
            self.render('{{ global_settings("tests.tEstgLobALsEttIng").title }}'),
            self.default_global_settings.title,
        )

    def test_models_cached(self):
        """Accessing a setting should only hit the DB once per render"""
        request = self.get_request()
        context = {"request": request}
        get_title = '{{ global_settings("tests.testglobalsetting").title }}'

        # Force-fetch site beforehand.
        Site.find_for_request(request)

        with self.assertNumQueries(1):
            for i in range(1, 4):
                with self.subTest(attempt=i):
                    template = self.engine.from_string(get_title * i)
                    self.assertEqual(
                        template.render(context), self.default_global_settings.title * i
                    )

    def test_settings_no_request(self):
        """
        Check that {{ global_settings }} throws an error if it can not find a
        request to work with
        """
        context = {}

        # Without a request in the context, this should bail with an error
        template = '{{ global_settings("tests.testglobalsetting").title }}'
        with self.assertRaises(RuntimeError):
            self.render(template, context, request_context=False)
