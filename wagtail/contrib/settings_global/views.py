from functools import lru_cache

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.text import capfirst
from django.utils.translation import gettext as _

from wagtail.admin import messages
from wagtail.admin.panels import (
    ObjectList,
    TabbedInterface,
    extract_panel_definitions_from_model_class,
)
from wagtail.log_actions import log

from .permissions import user_can_edit_global_setting_type
from .registry import registry


def get_model_from_url_params(app_name, model_name):
    """
    retrieve a content type from an app_name / model_name combo.
    Throw Http404 if not a valid setting type
    """
    model = registry.get_by_natural_key(app_name, model_name)
    if model is None:
        raise Http404
    return model


@lru_cache()
def get_global_setting_edit_handler(model):
    if hasattr(model, "edit_handler"):
        edit_handler = model.edit_handler
    else:
        panels = extract_panel_definitions_from_model_class(model)
        edit_handler = ObjectList(panels)
    return edit_handler.bind_to_model(model)


def get_or_create_then_redirect(request, app_name, model_name):
    model = get_model_from_url_params(app_name, model_name)

    return redirect(
        "wagtailglobalsettings:edit",
        app_name,
        model_name,
        model.for_request(request=request).id,
    )


def edit(request, app_name, model_name, pk):
    model = get_model_from_url_params(app_name, model_name)
    if not user_can_edit_global_setting_type(request.user, model):
        raise PermissionDenied

    setting_type_name = model._meta.verbose_name

    queryset = model.base_queryset()
    instance, created = queryset.get_or_create(id=pk)

    edit_handler = get_global_setting_edit_handler(model)
    form_class = edit_handler.get_form_class()

    if request.method == "POST":
        form = form_class(
            request.POST, request.FILES, instance=instance, for_user=request.user
        )

        if form.is_valid():
            with transaction.atomic():
                form.save()
                log(instance, "wagtail.edit")

            messages.success(
                request,
                _("%(setting_type)s updated.")
                % {"setting_type": capfirst(setting_type_name), "instance": instance},
            )
            return redirect("wagtailglobalsettings:edit", app_name, model_name)
        else:
            messages.validation_error(
                request, _("The setting could not be saved due to errors."), form
            )
    else:
        form = form_class(instance=instance, for_user=request.user)

    edit_handler = edit_handler.get_bound_panel(
        instance=instance, request=request, form=form
    )

    media = form.media + edit_handler.media

    return TemplateResponse(
        request,
        "wagtailglobalsettings/edit.html",
        {
            "opts": model._meta,
            "setting_type_name": setting_type_name,
            "instance": instance,
            "edit_handler": edit_handler,
            "form": form,
            "tabbed": isinstance(edit_handler.panel, TabbedInterface),
            "media": media,
        },
    )
