from django.test import TestCase, override_settings

from wagtail.models import Site
from wagtail.test.testapp.models import ImportantPagesGlobalSetting

from .base import GlobalSettingsTestMixin


@override_settings(ALLOWED_HOSTS=["localhost", "other"])
class GlobalSettingModelTestCase(GlobalSettingsTestMixin, TestCase):
    def _create_importantpagesglobalsetting_object(self):
        return ImportantPagesGlobalSetting.objects.create(
            sign_up_page=self.root_page,
            general_terms_page=self.root_page,
            privacy_policy_page=self.other_root_page,
        )

    def test_select_related(self, expected_queries=4):
        """The `select_related` attribute on setting models is `None` by default, so fetching foreign keys values requires additional queries"""
        request = self.get_request()

        self._create_importantpagesglobalsetting_object()

        # fetch settings and access foreign keys
        with self.assertNumQueries(expected_queries):
            settings = ImportantPagesGlobalSetting.for_request(request=request)
            settings.sign_up_page
            settings.general_terms_page
            settings.privacy_policy_page

    def test_select_related_use_reduces_total_queries(self):
        """But, `select_related` can be used to reduce the number of queries needed to fetch foreign keys"""
        try:
            # set class attribute temporarily
            ImportantPagesGlobalSetting.select_related = [
                "sign_up_page",
                "general_terms_page",
                "privacy_policy_page",
            ]
            self.test_select_related(expected_queries=1)
        finally:
            # undo temporary change
            ImportantPagesGlobalSetting.select_related = None

    def test_get_page_url_caches_page_urls(self):
        self._create_importantpagesglobalsetting_object()

        request = self.get_request()
        settings = ImportantPagesGlobalSetting.for_request(request=request)

        # Force-fetch some queries beforehand.
        Site.find_for_request(request)
        self.root_page._get_site_root_paths(request)
        self.other_root_page._get_site_root_paths(request)

        for page_fk_field, expected_result in (
            ("sign_up_page", "/"),
            ("general_terms_page", "/"),
            ("privacy_policy_page", "/other-root/"),
        ):
            with self.subTest(page_fk_field=page_fk_field):
                with self.assertNumQueries(1):
                    # because results are cached, only the first
                    # request for an attribute will trigger a query to
                    # fetch the page

                    # First fetch - direct (fetch from DB, then cache)
                    self.assertEqual(
                        settings.get_page_url(page_fk_field), expected_result
                    )

                    # Second fetch - direct (return from cache)
                    self.assertEqual(
                        settings.get_page_url(page_fk_field), expected_result
                    )

                    # Third fetch - indirect via shortcut (return from cache)
                    self.assertEqual(
                        getattr(settings.page_url, page_fk_field), expected_result
                    )

    def test_get_page_url_raises_attributeerror_if_attribute_name_invalid(self):
        settings = self._create_importantpagesglobalsetting_object()
        # when called directly
        with self.assertRaises(AttributeError):
            settings.get_page_url("not_an_attribute")
        # when called indirectly via shortcut
        with self.assertRaises(AttributeError):
            settings.page_url.not_an_attribute

    def test_get_page_url_returns_empty_string_if_attribute_value_not_a_page(self):
        settings = self._create_importantpagesglobalsetting_object()
        for value in (None, self.default_site):
            with self.subTest(attribute_value=value):
                settings.test_attribute = value
                # when called directly
                self.assertEqual(settings.get_page_url("test_attribute"), "")
                # when called indirectly via shortcut
                self.assertEqual(settings.page_url.test_attribute, "")
