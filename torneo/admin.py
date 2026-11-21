from django.contrib import admin
from .models import Juego, Liga, Torneo, Inscripcion, ResultadoTorneo, ReglaPuntuacionTorneo
from .forms import JuegoForm


@admin.register(Juego)
class JuegoAdmin(admin.ModelAdmin):
    form = JuegoForm
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


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "inscripcion_usuario",
        "inscripcion_torneo",
        "inscripcion_estado",
        "inscripcion_precio",
        "inscripcion_fecha",
    )

    list_filter = ("inscripcion_estado",)
    search_fields = (
        "inscripcion_usuario__username",
        "inscripcion_torneo__torneo_nombre",
    )

    readonly_fields = ("inscripcion_fecha",)
    
@admin.register(ResultadoTorneo)
class ResultadoTorneoAdmin(admin.ModelAdmin):
    list_display = (
        "inscripcion",
        "participo",
        "victorias",
        "empates",
        "derrotas",
        "posicion_final",
    )


@admin.register(ReglaPuntuacionTorneo)
class ReglaPuntuacionTorneoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "puntos_victoria",
        "puntos_empate",
        "puntos_derrota",
    )
