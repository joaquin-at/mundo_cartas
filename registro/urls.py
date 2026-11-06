from django.urls import path

from . import views


urlpatterns = [
    path("registro/", views.registrar_usuario, name="registro"),
    path("iniciar_sesion/", views.iniciar_sesion, name="iniciar_sesion"),
]
