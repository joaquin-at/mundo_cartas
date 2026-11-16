from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from registro.models import Perfil
from django.db import transaction
from django.db.models import Count
from django.db.models.deletion import ProtectedError, RestrictedError
from django.views.decorators.http import require_http_methods
from .forms import ConfirmarEliminarTorneoForm, JuegoForm, TorneoForm
from .models import Juego, Torneo
from .presentacion import normalizar_nombre

def administrador_requerido(vista):
    @wraps(vista)
    @login_required
    def wrapper(request, *args, **kwargs):
        es_administrador = Perfil.objects.filter(
            user=request.user,
            rol__nombre="Administrador"
        ).exists()

        if not es_administrador:
            raise PermissionDenied(
                "No tienes permisos de administrador."
            )

        return vista(request, *args, **kwargs)

    return wrapper

# LISTADO PÚBLICO
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

# LISTAR TODOS LOS TORNEOS
@administrador_requerido
def admin_listar_torneos(request):
    torneos = (
        Torneo.objects
        .select_related("torneo_juego", "torneo_liga")
        .order_by("-torneo_inicio")
    )

    return render(
        request,
        "torneo/admin_listar.html",
        {"torneos": torneos}
    )

# CREAR TORNEO
@administrador_requerido
def admin_crear_torneo(request):

    if request.method == "POST":
        form = TorneoForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Torneo creado correctamente."
            )

            return redirect("admin_listar_torneos")

    else:
        form = TorneoForm()

    return render(
        request,
        "torneo/admin_crear.html",
        {
            "form": form,
        }
    )

# ACTUALIZAR TORNEO
@administrador_requerido
def admin_actualizar_torneo(request, pk):
    torneo = get_object_or_404(Torneo, pk=pk)

    if request.method == "POST":
        form = TorneoForm(
            request.POST,
            instance=torneo
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Torneo actualizado correctamente."
            )

            return redirect("admin_listar_torneos")
    else:
        form = TorneoForm(instance=torneo)

    return render(
        request,
        "torneo/admin_actualizar.html",
        {
            "form": form,
            "torneo": torneo,
        }
    )

# CANCELAR O ELIMINAR TORNEOS
@administrador_requerido
@require_http_methods(["GET", "POST"])
def admin_cancelar_torneo(request, pk):
    torneo = get_object_or_404(Torneo, pk=pk)
    if request.method == "POST":
        if torneo.torneo_estado != "Cancelado":
            torneo.torneo_estado = "Cancelado"
            torneo.save(update_fields=["torneo_estado"])
            messages.success(request, "Torneo cancelado. Se conserva su historial.")
        else:
            messages.info(request, "El torneo ya estaba cancelado.")
        return redirect("admin_listar_torneos")
    return render(request, "torneo/admin_cancelar.html", {"torneo": torneo})


@administrador_requerido
@require_http_methods(["GET", "POST"])
def admin_eliminar_torneo(request, pk):
    torneo = get_object_or_404(Torneo, pk=pk)
    form = ConfirmarEliminarTorneoForm(request.POST if request.method == "POST" else None)
    estado_respuesta = 200
    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    torneo.delete()
            except (ProtectedError, RestrictedError):
                form.add_error(None, "No se puede eliminar porque existen registros relacionados. Puedes cancelar el torneo para conservarlos.")
                estado_respuesta = 409
            else:
                messages.success(request, "Torneo eliminado definitivamente.")
                return redirect("admin_listar_torneos")
        else:
            estado_respuesta = 400
    return render(request, "torneo/admin_eliminar.html", {"torneo": torneo, "form": form}, status=estado_respuesta)


@administrador_requerido
@require_http_methods(["GET"])
def admin_listar_juegos(request):
    juegos = Juego.objects.annotate(
        total_torneos=Count("torneos", distinct=True),
        total_ligas=Count("ligas", distinct=True),
    ).order_by("juego_nombre")
    busqueda = request.GET.get("q", "").strip()[:100]
    estado = request.GET.get("estado", "todos")
    if estado not in {"todos", "activos", "inactivos"}:
        estado = "todos"
    if estado != "todos":
        juegos = juegos.filter(juego_activo=(estado == "activos"))
    filtro = normalizar_nombre(busqueda)
    juegos = [juego for juego in juegos if not filtro or filtro in normalizar_nombre(juego.juego_nombre)]
    return render(request, "torneo/admin_juegos.html", {
        "juegos": juegos, "busqueda": busqueda, "estado": estado, "total": len(juegos),
    })


@administrador_requerido
@require_http_methods(["GET", "POST"])
def admin_crear_juego(request):
    form = JuegoForm(request.POST if request.method == "POST" else None, request.FILES if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Juego creado correctamente.")
        return redirect("admin_listar_juegos")
    return render(request, "torneo/admin_juego_formulario.html", {
        "form": form, "titulo": "Crear juego", "texto_boton": "Crear juego",
    })


@administrador_requerido
@require_http_methods(["GET", "POST"])
def admin_actualizar_juego(request, pk):
    juego = get_object_or_404(Juego, pk=pk)
    form = JuegoForm(request.POST if request.method == "POST" else None, request.FILES if request.method == "POST" else None, instance=juego)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Juego actualizado correctamente.")
        return redirect("admin_listar_juegos")
    return render(request, "torneo/admin_juego_formulario.html", {
        "form": form, "juego": juego, "titulo": "Editar juego", "texto_boton": "Guardar cambios",
    })


@administrador_requerido
@require_http_methods(["GET", "POST"])
def admin_desactivar_juego(request, pk):
    juego = get_object_or_404(Juego, pk=pk)
    if request.method == "POST":
        if juego.juego_activo:
            juego.juego_activo = False
            juego.save(update_fields=["juego_activo"])
            messages.success(request, "Juego desactivado. Sus torneos y ligas se conservan.")
        return redirect("admin_listar_juegos")
    return render(request, "torneo/admin_juego_desactivar.html", {"juego": juego})