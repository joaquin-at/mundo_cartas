from django.urls import path
from . import views


urlpatterns = [
    path("", views.listar_torneos,name="listar_torneos"),
    path("administrar/", views.admin_listar_torneos, name="admin_listar_torneos"),
    path("administrar/crear/", views.admin_crear_torneo, name="admin_crear_torneo"),
    path("administrar/<int:pk>/actualizar/", views.admin_actualizar_torneo, name="admin_actualizar_torneo"),
    path("administrar/<int:pk>/cancelar/", views.admin_cancelar_torneo, name="admin_cancelar_torneo"),
    path("administrar/<int:pk>/eliminar/", views.admin_eliminar_torneo, name="admin_eliminar_torneo"),
    path("<int:pk>/inscribirse/", views.solicitar_inscripcion, name="solicitar_inscripcion"),
    path("administrar/resultados/", views.admin_resultados_torneos, name="admin_resultados_torneos"),
    path("administrar/resultados/<int:pk>/", views.admin_resultados_detalle, name="admin_resultados_detalle"),
    path("administrar/resultados/<int:pk>/inscripcion/<int:inscripcion_id>/", views.admin_registrar_resultado, name="admin_registrar_resultado"),

    
]