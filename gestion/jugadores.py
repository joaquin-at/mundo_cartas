from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render
from .views import _exigir_administrador


def _jugadores():
    return get_user_model().objects.filter(
        perfil__rol__nombre="Jugador", is_staff=False, is_superuser=False,
    ).select_related("perfil__rol")


@login_required
def admin_listar_jugadores(request):
    _exigir_administrador(request)
    jugadores = _jugadores()
    busqueda = request.GET.get("q", "").strip()[:100]
    estado = request.GET.get("estado", "todos")
    if estado not in ("todos", "activos", "inactivos"):
        estado = "todos"
    if busqueda:
        jugadores = jugadores.filter(
            Q(username__icontains=busqueda) | Q(first_name__icontains=busqueda)
            | Q(last_name__icontains=busqueda) | Q(email__icontains=busqueda)
            | Q(perfil__telefono__icontains=busqueda)
        )
    if estado in ("activos", "inactivos"):
        jugadores = jugadores.filter(is_active=estado == "activos")
    jugadores = jugadores.annotate(inscripciones_total=Count("inscripciones", distinct=True))
    pagina = Paginator(jugadores.order_by("username", "pk"), 20).get_page(request.GET.get("pagina"))
    filtros = urlencode({"q": busqueda, "estado": estado})
    return render(request, "gestion/admin_jugadores.html", {
        "jugadores": pagina, "busqueda": busqueda, "estado": estado,
        "filtros": filtros,
    })
