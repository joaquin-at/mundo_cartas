from django.urls import path
from . import views


urlpatterns = [
    path("", views.inicioView, name="inicio"),
    path(
        "gestion/panel/",
        views.panel_administrador,
        name="panel_administrador",
    ),
]