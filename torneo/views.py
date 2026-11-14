from django.shortcuts import render
from .models import Torneo
# Create your views here.

def listar_torneos(request):
    torneos = (
        Torneo.objects
        .filter(torneo_estado="Publicado")
        .select_related("torneo_juego", "torneo_liga")
        .order_by("torneo_inicio")
    )

    return render(
        request,
        "torneo/listar.html",
        {"torneos": torneos}
    )
