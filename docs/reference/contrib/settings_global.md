# Global settings

You can define global settings that are for all sites that are editable by administrators in the Wagtail admin. Global settings can be accessed in code as well as in templates.

## Installation

Add `wagtail.contrib.settings_global` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS += [
    'wagtail.contrib.settings_global',
]
```

## Defining settings

Create a model that inherits from `BaseGlobalSetting`, and register it using the `register_global_setting` decorator:

```python
from django.db import models
from wagtail.contrib.settings_global.models import BaseGlobalSetting, register_global_setting

@register_global_setting
class SocialMediaSettings(BaseGlobalSetting):
    facebook = models.URLField(
        help_text='Your Facebook page URL')
    instagram = models.CharField(
        max_length=255, help_text='Your Instagram username, without the @')
    trip_advisor = models.URLField(
        help_text='Your Trip Advisor page URL')
    youtube = models.URLField(
        help_text='Your YouTube channel or user account URL')
```

A 'Social media settings' link will appear in the Wagtail admin 'Settings' menu.

## Edit handlers

Global settings use edit handlers much like the rest of Wagtail. Add a `panels` setting to your model defining all the edit handlers required:

```python
@register_global_setting
class ImportantPages(BaseGlobalSetting):
    donate_page = models.ForeignKey(
        'wagtailcore.Page', null=True, on_delete=models.SET_NULL, related_name='+')
    sign_up_page = models.ForeignKey(
        'wagtailcore.Page', null=True, on_delete=models.SET_NULL, related_name='+')

    panels = [
        FieldPanel('donate_page'),
        FieldPanel('sign_up_page'),
    ]
```

You can also customize the editor handlers [like you would do for Page model](/advanced_topics/customisation/page_editing_interface.html#customising-the-tabbed-interface) with a custom `edit_handler` attribute:

```python
from wagtail.admin.panels import TabbedInterface, ObjectList

@register_global_setting
class MySettings(BaseGlobalSetting):
    # ...
    first_tab_panels = [
        FieldPanel('field_1'),
    ]
    second_tab_panels = [
        FieldPanel('field_2'),
    ]

    edit_handler = TabbedInterface([
        ObjectList(first_tab_panels, heading='First tab'),
        ObjectList(second_tab_panels, heading='Second tab'),
    ])
```

## Appearance

You can change the label used in the menu by changing the `django.db.models.Options.verbose_name` of your model.

You can add an icon to the menu by passing an `icon` argument to the `register_global_setting` decorator:

```python
@register_global_setting(icon='placeholder')
class SocialMediaSettings(BaseGlobalSetting):
    class Meta:
        verbose_name = 'social media accounts'
    ...
```

For a list of all available icons, please see the [styleguide](/contributing//styleguide.html).

## Using the global settings

Global settings are designed to be used both in Python code and in templates.

### Using in Python

If you require access to a global setting in a view, the `wagtail.contrib.settings_global.models.BaseGlobalSetting.for_request` method allows you to retrieve the global settings for the current request:

```python
def view(request):
    social_media_settings = SocialMediaSettings.for_request(request)
    ...
```

### Using in Django templates

Add the `wagtail.contrib.settings_global.context_processors.global_settings` context processor to your settings:

```python
TEMPLATES = [
    {
        ...

        'OPTIONS': {
            'context_processors': [
                ...

                'wagtail.contrib.settings_global.context_processors.global_settings',
            ]
        }
    }
]
```

Then access the global settings through `{{ global_settings }}`:

```html+django
{{ global_settings.app_label.SocialMediaSettings.instagram }}
```

**Note:** Replace `app_label` with the label of the app containing your settings model.

If you are not in a `RequestContext`, then context processors will not have run, and the `settings_global` variable will not be available. To get the `settings_global`, use the provided `{% get_global_settings %}` template tag.

```html+django
{% load wagtailglobalsettings_tags %}
{% get_global_settings %}
{{ global_settings.app_label.SocialMediaSettings.instagram }}
```

By default, the tag will create or update a `global_settings` variable in the context. If you want to
assign to a different context variable instead, use `{% get_global_settings as other_variable_name %}`:

```html+django
{% load wagtailglobalsettings_tags %}
{% get_global_settings as wagtail_settings %}
{{ wagtail_settings.app_label.SocialMediaSettings.instagram }}
```

### Using in Jinja2 templates

Add `wagtail.contrib.settings_global.jinja2tags.global_settings` extension to your Jinja2 settings:

```python
TEMPLATES = [
    ...

    {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'APP_DIRS': True,
        'OPTIONS': {
            'extensions': [
                ...

                'wagtail.contrib.settings_global.jinja2tags.global_settings',
            ],
        },
    }
]
```

Then access the settings through the `global_settings()` template function:

```html+jinja
{{ global_settings("app_label.SocialMediaSettings").twitter }}
```

**Note:** Replace `app_label` with the label of the app containing your settings model.

This will look for a `request` variable in the template context, and find the correct site to use from that.

You can store the settings instance in a variable to save some typing, if you have to use multiple values from one model:

```html+jinja
{% with social_settings=global_settings("app_label.SocialMediaSettings") %}
    Follow us on Twitter at @{{ social_settings.twitter }},
    or Instagram at @{{ social_settings.instagram }}.
{% endwith %}
```

Or, alternately, using the `set` tag:

```html+jinja
{% set social_settings=global_settings("app_label.SocialMediaSettings") %}
```

## Utilising `select_related` to improve efficiency

For models with foreign key relationships to other objects (e.g. pages),
which are very often needed to output values in templates, you can set
the `select_related` attribute on your model to have Wagtail utilise
Django's [QuerySet.select_related()](https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-related)
method to fetch the settings object and related objects in a single query.
With this, the initial query is more complex, but you will be able to
freely access the foreign key values without any additional queries,
making things more efficient overall.

Building on the `ImportantPages` example from the previous section, the
following shows how `select_related` can be set to improve efficiency:

```python
@register_global_setting
class ImportantPages(BaseGlobalSetting):

    # Fetch these pages when looking up ImportantPages for or a site
    select_related = ["donate_page", "sign_up_page"]

    donate_page = models.ForeignKey(
        'wagtailcore.Page', null=True, on_delete=models.SET_NULL, related_name='+')
    sign_up_page = models.ForeignKey(
        'wagtailcore.Page', null=True, on_delete=models.SET_NULL, related_name='+')

    panels = [
        FieldPanel('donate_page'),
        FieldPanel('sign_up_page'),
    ]
```

With these additions, the following template code will now trigger
a single database query instead of three (one to fetch the settings,
and two more to fetch each page):

```html+django
{% load wagtailcore_tags %}
{% pageurl global_settings.app_label.ImportantPages.donate_page %}
{% pageurl global_settings.app_label.ImportantPages.sign_up_page %}
```

## Utilising the `page_url` setting shortcut

If, like in the previous section, your settings model references pages,
and you often need to output the URLs of those pages in your project,
you can likely use the setting model's `page_url` shortcut to do that more
cleanly. For example, instead of doing the following:

```html+django
{% load wagtailcore_tags %}
{% pageurl settings.app_label.ImportantPages.donate_page %}
{% pageurl settings.app_label.ImportantPages.sign_up_page %}
```

You could write:

```html+django
{{ global_settings.app_label.ImportantPages.page_url.donate_page }}
{{ global_settings.app_label.ImportantPages.page_url.sign_up_page }}
```

Using the `page_url` shortcut has a few of advantages over using the tag:

1.  The 'specific' page is automatically fetched to generate the URL,
    so you don't have to worry about doing this (or forgetting to do this)
    yourself.
2.  The results are cached, so if you need to access the same page URL
    in more than one place (e.g. in a form and in footer navigation), using
    the `page_url` shortcut will be more efficient.
3.  It's more concise, and the syntax is the same whether using it in templates
    or views (or other Python code), allowing you to write more consistent
    code.

When using the `page_url` shortcut, there are a couple of points worth noting:

1.  The same limitations that apply to the `{% pageurl %}` tag apply to the
    shortcut: If the settings are accessed from a template context where the
    current request is not available, all URLs returned will include the
    site's scheme/domain, and URL generation will not be quite as efficient.
2.  If using the shortcut in views or other Python code, the method will
    raise an `AttributeError` if the attribute you request from `page_url`
    is not an attribute on the settings object.
3.  If the settings object DOES have the attribute, but the attribute returns
    a value of `None` (or something that is not a `Page`), the shortcut
    will return an empty string.
