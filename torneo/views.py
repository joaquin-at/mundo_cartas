
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
from .forms import TorneoForm
from .models import Torneo


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


# ELIMINAR TORNEO (CANCELACIÓN LÓGICA)
@administrador_requerido
def admin_eliminar_torneo(request, pk):
    torneo = get_object_or_404(Torneo, pk=pk)

    if request.method == "POST":
        if torneo.torneo_estado != "Cancelado":
            torneo.torneo_estado = "Cancelado"
            torneo.save(update_fields=["torneo_estado"])

            messages.success(
                request,
                "Torneo cancelado correctamente."
            )

        return redirect("admin_listar_torneos")

    return render(
        request,
        "torneo/admin_eliminar.html",
        {"torneo": torneo}
    )
