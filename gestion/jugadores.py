from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from registro.forms import CustomUserCreationForm, PerfilUsuarioForm
from registro.models import Perfil, Rol
from .forms import ConfirmarAccionJugadorForm, SolicitudDesactivacionForm
from .views import _exigir_administrador, _mostrar_perfil


def _jugadores():
    return get_user_model().objects.filter(
        perfil__rol__nombre="Jugador", is_staff=False, is_superuser=False,
    ).select_related("perfil__rol")


def _buscar_jugador(pk, bloquear=False):
    if pk > 9223372036854775807:
        raise Http404
    jugadores = _jugadores()
    if bloquear:
        jugadores = jugadores.select_for_update()
    return get_object_or_404(jugadores, pk=pk)


@login_required
def admin_listar_jugadores(request):
    _exigir_administrador(request)
    jugadores = _jugadores()
    busqueda = request.GET.get("q", "").strip()[:100]
    estado = request.GET.get("estado", "todos")
    if estado not in ("todos", "activos", "inactivos", "solicitudes"):
        estado = "todos"
    if busqueda:
        jugadores = jugadores.filter(
            Q(username__icontains=busqueda) | Q(first_name__icontains=busqueda)
            | Q(last_name__icontains=busqueda) | Q(email__icontains=busqueda)
            | Q(perfil__telefono__icontains=busqueda)
        )
    if estado in ("activos", "inactivos"):
        jugadores = jugadores.filter(is_active=estado == "activos")
    elif estado == "solicitudes":
        jugadores = jugadores.filter(is_active=True, perfil__desactivacion_solicitada_el__isnull=False)
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


@login_required
@require_http_methods(["GET", "POST"])
def admin_estado_jugador(request, pk, accion):
    _exigir_administrador(request)
    opciones = {
        "desactivar": ("Desactivar jugador", "La cuenta perderá el acceso, pero conservará su perfil, torneos, pagos y comentarios."),
        "activar": ("Reactivar jugador", "El jugador podrá volver a iniciar sesión con su cuenta y contraseña actuales."),
        "rechazar": ("Rechazar solicitud", "La cuenta seguirá activa y el jugador podrá continuar utilizando la plataforma."),
    }
    if accion not in opciones:
        raise Http404
    jugador = _buscar_jugador(pk)
    form = ConfirmarAccionJugadorForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            jugador = _buscar_jugador(pk, bloquear=True)
            perfil = Perfil.objects.select_for_update().get(user=jugador)
            if accion == "rechazar" and not perfil.desactivacion_solicitada_el:
                messages.info(request, "El jugador ya no tiene una solicitud pendiente.")
                return redirect("admin_listar_jugadores")
            if accion != "rechazar":
                jugador.is_active = accion == "activar"
                jugador.save(update_fields=["is_active"])
            perfil.desactivacion_solicitada_el = None
            perfil.motivo_desactivacion = ""
            perfil.save(update_fields=["desactivacion_solicitada_el", "motivo_desactivacion"])
        mensajes = {
            "desactivar": "Cuenta desactivada. Su historial se conserva.",
            "activar": "Cuenta reactivada correctamente.",
            "rechazar": "Solicitud rechazada. La cuenta continúa activa.",
        }
        messages.success(request, mensajes[accion])
        return redirect("admin_listar_jugadores")
    titulo, descripcion = opciones[accion]
    return render(request, "gestion/admin_jugador_formulario.html", {
        "form": form, "jugador": jugador, "titulo": titulo,
        "texto_boton": titulo, "descripcion": descripcion,
    })


@login_required
@require_POST
def solicitar_desactivacion(request):
    if not _jugadores().filter(pk=request.user.pk).exists():
        raise PermissionDenied
    form = SolicitudDesactivacionForm(request.POST)
    if not form.is_valid():
        return _mostrar_perfil(request, form_desactivacion=form)
    with transaction.atomic():
        perfil = Perfil.objects.select_for_update().get(user=request.user)
        if perfil.desactivacion_solicitada_el:
            messages.info(request, "Ya tienes una solicitud pendiente de revisión.")
        else:
            perfil.desactivacion_solicitada_el = timezone.now()
            perfil.motivo_desactivacion = form.cleaned_data["motivo"]
            perfil.save(update_fields=["desactivacion_solicitada_el", "motivo_desactivacion"])
            messages.success(request, "Solicitud enviada. Tu cuenta seguirá activa hasta que el administrador la revise.")
    return redirect("mi_perfil")


@login_required
@require_POST
def cancelar_desactivacion(request):
    if not _jugadores().filter(pk=request.user.pk).exists():
        raise PermissionDenied
    Perfil.objects.filter(user=request.user).update(desactivacion_solicitada_el=None, motivo_desactivacion="")
    messages.success(request, "Solicitud cancelada. Tu cuenta continúa activa.")
    return redirect("mi_perfil")