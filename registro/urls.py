from django.urls import path

from . import views


urlpatterns = [
    path("iniciar_sesion/", views.iniciar_sesion, name="iniciar_sesion"),
]
