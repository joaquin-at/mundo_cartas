from django.urls import path
from . import views
from torneo import views as torneo_views


urlpatterns = [
    path("", views.inicioView, name="inicio"),
    path("gestion/panel/", views.panel_administrador, name="panel_administrador"),
    path("mi-perfil/", views.mi_perfil, name="mi_perfil"),
    path("clasificacion/", views.clasificacion, name="clasificacion"),
    path("juegos/", views.listar_juegos, name="listar_juegos"),
    path("juegos/<int:pk>/", views.detalle_juego, name="detalle_juego"),
    path("gestion/juegos/", torneo_views.admin_listar_juegos, name="admin_listar_juegos"),
    path("gestion/juegos/crear/", torneo_views.admin_crear_juego, name="admin_crear_juego"),
    path("gestion/juegos/<int:pk>/editar/", torneo_views.admin_actualizar_juego, name="admin_actualizar_juego"),
    path("gestion/juegos/<int:pk>/desactivar/", torneo_views.admin_desactivar_juego, name="admin_desactivar_juego"),
]
