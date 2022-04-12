from django.urls import path

from . import views

app_name = "wagtailsettings"
urlpatterns = [
    path(
        "<slug:app_name>/<slug:model_name>/",
        views.redirect_to_relevant_instance,
        name="edit",
    ),  # TODO: rename and handle both abstract models
    path(
        "<slug:app_name>/<slug:model_name>/<int:pk>/", views.edit, name="edit"
    ),  # TODO: change from site to generic pk
]
