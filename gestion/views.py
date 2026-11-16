from torneo.presentacion import (
    normalizar_nombre as _nombre_normalizado,
    presentacion_juego as _presentacion_juego,
)

from django.db.models import Count, Q
from torneo.models import Juego
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from registro.models import Perfil
from registro.forms import PerfilUsuarioForm
from django.contrib import messages
from django.views.decorators.http import require_http_methods

def inicioView(request):
    juegos = Juego.objects.filter(juego_activo=True).order_by("juego_nombre")
    tarjetas = [_presentacion_juego(juego) for juego in juegos]
    return render(request, "gestion/index.html", {"tarjetas_inicio": tarjetas})

@login_required
def panel_administrador(request):
    es_administrador = Perfil.objects.filter(
        user=request.user,
        rol__nombre="Administrador",
    ).exists()

    if not es_administrador:
        return redirect("inicio")

    return render(request, "gestion/panel_administrador.html")

@login_required
@require_http_methods(["GET", "POST"])
def mi_perfil(request):
    form = PerfilUsuarioForm(
        request.POST if request.method == "POST" else None,
        instance=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perfil actualizado correctamente.")
        return redirect("mi_perfil")
    return render(request, "gestion/mi_perfil.html", {
        "form": form,
        "editar_perfil": request.method == "POST" or request.GET.get("editar") == "1",
    })

def clasificacion(request):
    return render(request, "gestion/clasificacion.html")



def listar_juegos(request):
    juegos = Juego.objects.filter(juego_activo=True).annotate(
        torneos_publicados=Count("torneos", filter=Q(torneos__torneo_estado="Publicado"))
    ).order_by("juego_nombre")
    busqueda = request.GET.get("q", "").strip()[:100]
    filtro = _nombre_normalizado(busqueda)
    tarjetas = [
        _presentacion_juego(juego) for juego in juegos
        if not filtro or filtro in _nombre_normalizado(juego.juego_nombre)
    ]
    return render(request, "gestion/juegos.html", {"tarjetas": tarjetas, "busqueda": busqueda})


def detalle_juego(request, pk):
    juego = get_object_or_404(Juego, pk=pk, juego_activo=True)
    torneos = juego.torneos.filter(torneo_estado="Publicado").select_related("torneo_juego").order_by("torneo_inicio")
    return render(request, "gestion/detalle_juego.html", {
        "tarjeta": _presentacion_juego(juego), "juego": juego, "torneos": torneos,
    })
