from django.urls import path
from . import views


urlpatterns = [
    path("", views.listar_torneos,name="listar_torneos"),
    path("administrar/", views.admin_listar_torneos, name="admin_listar_torneos"),
    path("administrar/crear/", views.admin_crear_torneo, name="admin_crear_torneo"),
    path("administrar/<int:pk>/actualizar/", views.admin_actualizar_torneo, name="admin_actualizar_torneo"),
    path("administrar/<int:pk>/cancelar/", views.admin_cancelar_torneo, name="admin_cancelar_torneo"),
    path("administrar/<int:pk>/eliminar/", views.admin_eliminar_torneo, name="admin_eliminar_torneo"),
]