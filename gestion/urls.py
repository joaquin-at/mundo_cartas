from django.urls import path
from . import views
from torneo import views as torneo_views


urlpatterns = [
    path("", views.inicioView, name="inicio"),
    path("gestion/panel/", views.panel_administrador, name="panel_administrador"),
    path("gestion/comentarios/",views.admin_comentarios_sugerencias,name="admin_comentarios_sugerencias",),
    path("mi-perfil/", views.mi_perfil, name="mi_perfil"),
    path("mi-perfil/foto/", views.actualizar_foto_perfil, name="actualizar_foto_perfil"),
    path("mi-perfil/enviar-comentario/",views.enviar_comentario_sugerencia,name="enviar_comentario_sugerencia",),
    path("gestion/comentarios/eliminar/",views.admin_eliminar_comentarios,name="admin_eliminar_comentarios",),
    path("gestion/comentarios/<int:pk>/estado/",views.admin_cambiar_estado_comentario,name="admin_cambiar_estado_comentario",),
    path("mi-perfil/historial/", views.historial_torneos, name="historial_torneos"),
    path("clasificacion/", views.clasificacion, name="clasificacion"),
    path("juegos/", views.listar_juegos, name="listar_juegos"),
    path("juegos/<int:pk>/", views.detalle_juego, name="detalle_juego"),
    path("gestion/juegos/", torneo_views.admin_listar_juegos, name="admin_listar_juegos"),
    path("gestion/juegos/crear/", torneo_views.admin_crear_juego, name="admin_crear_juego"),
    path("gestion/juegos/<int:pk>/editar/", torneo_views.admin_actualizar_juego, name="admin_actualizar_juego"),
    path("gestion/juegos/<int:pk>/desactivar/", torneo_views.admin_desactivar_juego, name="admin_desactivar_juego"),
]
