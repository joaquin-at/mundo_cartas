
from django.contrib import admin
from .models import Juego, Liga, Torneo


@admin.register(Juego)
class JuegoAdmin(admin.ModelAdmin):
    list_display = ("id", "juego_nombre", "juego_activo")


@admin.register(Liga)
class LigaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "liga_nombre",
        "liga_juego",
        "liga_inicio",
        "liga_fin",
        "liga_estado",
    )


@admin.register(Torneo)
class TorneoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "torneo_nombre",
        "torneo_juego",
        "torneo_liga",
        "torneo_inicio",
        "torneo_estado",
    )
    list_filter = ("torneo_estado", "torneo_juego")
    search_fields = ("torneo_nombre",)
