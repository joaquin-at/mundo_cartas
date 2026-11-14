from django.urls import path
from . import views

urlpatterns = [
    path("", views.listar_torneos, name="listar_torneos"),
]
