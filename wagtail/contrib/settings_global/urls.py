from django.urls import path

from . import views

app_name = "wagtailglobalsettings"
urlpatterns = [
    path(
        "<slug:app_name>/<slug:model_name>/",
        views.get_or_create_then_redirect,
        name="edit",
    ),
    path("<slug:app_name>/<slug:model_name>/<int:pk>/", views.edit, name="edit"),
]
