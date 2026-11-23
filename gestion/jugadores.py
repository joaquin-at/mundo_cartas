from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404
from django.views.decorators.http import require_http_methods
from registro.forms import CustomUserCreationForm, PerfilUsuarioForm
from registro.models import Perfil, Rol
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


@login_required
@require_http_methods(["GET", "POST"])
def admin_crear_jugador(request):
    _exigir_administrador(request)
    form = CustomUserCreationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                usuario = form.save()
                rol, _ = Rol.objects.get_or_create(nombre="Jugador")
                Perfil.objects.create(user=usuario, rol=rol, telefono=form.cleaned_data["telefono"])
        except IntegrityError:
            form.add_error(None, "No se pudo crear la cuenta. Comprueba el nombre de usuario y vuelve a intentarlo.")
        else:
            messages.success(request, "Jugador creado correctamente.")
            return redirect("admin_listar_jugadores")
    return render(request, "gestion/admin_jugador_formulario.html", {
        "form": form, "titulo": "Crear jugador", "texto_boton": "Crear jugador",
        "descripcion": "La cuenta se creará activa y con el rol Jugador. Todos los campos marcados con * son obligatorios.",
    })


def _buscar_jugador(pk, bloquear=False):
    if pk > 9223372036854775807:
        raise Http404
    jugadores = _jugadores()
    if bloquear:
        jugadores = jugadores.select_for_update()
    return get_object_or_404(jugadores, pk=pk)


@login_required
@require_http_methods(["GET", "POST"])
def admin_editar_jugador(request, pk):
    _exigir_administrador(request)
    jugador = _buscar_jugador(pk)
    form = PerfilUsuarioForm(request.POST if request.method == "POST" else None, instance=jugador)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Datos del jugador actualizados correctamente.")
        return redirect("admin_listar_jugadores")
    return render(request, "gestion/admin_jugador_formulario.html", {
        "form": form, "jugador": jugador, "titulo": "Editar jugador", "texto_boton": "Guardar cambios",
        "descripcion": "Actualiza sus datos personales. La contraseña, el rol y el historial se conservan.",
    })
