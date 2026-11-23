from torneo.presentacion import (
    normalizar_nombre as _nombre_normalizado,
    presentacion_juego as _presentacion_juego,
)

from torneo.services import obtener_ranking_por_juego

from django.db.models import Count, Q,  F, Sum
from torneo.models import Inscripcion, Juego, ResultadoTorneo
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from registro.models import Perfil
from registro.forms import FotoPerfilForm, PerfilUsuarioForm
from django.contrib import messages
from django.views.decorators.http import require_http_methods , require_POST

from .forms import ComentarioSugerenciaForm

from django.core.exceptions import PermissionDenied
from .models import ComentarioSugerencia
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import OperationalError, models, transaction
from django.http import Http404, QueryDict
from django.urls import reverse
from django.utils import timezone
from .forms import EliminarComentariosForm, RespuestaComentarioForm, SeleccionComentariosForm

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
    return _mostrar_perfil(request, form_perfil=form)


def _mostrar_perfil(request, form_perfil=None, form_comentario=None, form_foto=None):
    if form_perfil is None:
        form_perfil = PerfilUsuarioForm(instance=request.user)
    es_jugador = Perfil.objects.filter(user=request.user, rol__nombre="Jugador").exists()
    comentarios_usuario = None
    if es_jugador:
        if form_foto is None:
            form_foto = FotoPerfilForm(instance=request.user.perfil)
        if form_comentario is None:
            form_comentario = ComentarioSugerenciaForm()
        comentarios_usuario = Paginator(
            ComentarioSugerencia.objects.filter(usuario=request.user).order_by("-fecha_envio", "-pk"), 5
        ).get_page(request.GET.get("mensajes_pagina"))

    inscripciones = (
        Inscripcion.objects
        .filter(
            inscripcion_usuario=request.user,
            inscripcion_estado="Confirmada",
        )
        .select_related("inscripcion_torneo__torneo_juego")
    )

    torneos_inscritos = (
        inscripciones
        .filter(inscripcion_torneo__torneo_estado="Publicado")
        .order_by("inscripcion_torneo__torneo_inicio")
    )

    historial_reciente = (
        inscripciones
        .filter(
            inscripcion_torneo__torneo_estado__in=[
                "Finalizado",
                "Cancelado",
            ]
        )
        .order_by("-inscripcion_torneo__torneo_inicio")[:3]
    )

    puntos_por_juego = [
        fila
        for fila in obtener_ranking_por_juego()
        if fila["jugador_id"] == request.user.pk
    ]

    return render(request, "gestion/mi_perfil.html", {
        "form": form_perfil,
        "editar_perfil": form_perfil.is_bound or request.GET.get("editar") == "1",
        "torneos_inscritos": torneos_inscritos,
        "historial_reciente": historial_reciente,
        "puntos_por_juego": puntos_por_juego,
        "es_jugador": es_jugador,
        "form_comentario": form_comentario,
        "comentarios_usuario": comentarios_usuario,
        "form_foto": form_foto,
        "editar_foto": form_foto is not None and (form_foto.is_bound or request.GET.get("foto") == "1"),
    })


@login_required
@require_POST
def actualizar_foto_perfil(request):
    perfil = get_object_or_404(Perfil.objects.select_related("rol"), user=request.user)
    if perfil.rol.nombre != "Jugador":
        raise PermissionDenied
    foto_anterior = perfil.foto.name
    almacenamiento = perfil.foto.storage
    form = FotoPerfilForm(request.POST, request.FILES, instance=perfil)
    if form.is_valid():
        with transaction.atomic():
            perfil = form.save(commit=False)
            if form.cleaned_data["quitar_foto"]:
                perfil.foto = ""
            perfil.save(update_fields=["foto"])
            if foto_anterior and foto_anterior != perfil.foto.name:
                transaction.on_commit(lambda: almacenamiento.delete(foto_anterior))
        messages.success(request, "Tu foto de perfil se actualizó correctamente.")
        return redirect(reverse("mi_perfil") + "#mis-datos")
    return _mostrar_perfil(request, form_foto=form)

def clasificacion(request):
    ranking = obtener_ranking_por_juego()

    return render(
        request,
        "gestion/clasificacion.html",{"ranking": ranking,},
    )



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

@login_required
def historial_torneos(request):
    
    historial = (
        Inscripcion.objects
        .filter(
            inscripcion_usuario=request.user,
            inscripcion_estado="Confirmada",
            inscripcion_torneo__torneo_estado__in=[
                "Finalizado",
                "Cancelado",
            ],
        )
        .select_related("inscripcion_torneo__torneo_juego")
        .order_by("-inscripcion_torneo__torneo_inicio")
    )

    return render(request, "gestion/historial_torneos.html", {
        "historial": historial,
    })


@login_required
@require_POST
def enviar_comentario_sugerencia(request):
    if not Perfil.objects.filter(user=request.user, rol__nombre="Jugador").exists():
        raise PermissionDenied

    form = ComentarioSugerenciaForm(request.POST)
    if form.is_valid():
        ahora = timezone.now()
        try:
            with transaction.atomic():
                # Serializa los envíos del mismo usuario en bases que admiten bloqueo de filas.
                get_user_model().objects.select_for_update().get(pk=request.user.pk)
                anteriores = ComentarioSugerencia.objects.filter(usuario=request.user)
                duplicado = anteriores.filter(
                    mensaje=form.cleaned_data["mensaje"],
                    fecha_envio__gte=ahora - timedelta(minutes=5),
                ).exists()
                if duplicado:
                    form.add_error(None, "Ya enviaste este mensaje. Puedes consultarlo en tus mensajes enviados.")
                elif anteriores.filter(fecha_envio__gte=ahora - timedelta(seconds=30)).exists():
                    form.add_error(None, "Espera 30 segundos entre envíos antes de enviar otro mensaje.")
                else:
                    comentario = form.save(commit=False)
                    comentario.usuario = request.user
                    comentario.tipo = "comentario"
                    comentario.save()
        except OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            form.add_error(None, "Hay otro envío en curso. Espera unos segundos y vuelve a intentarlo.")
        if not form.errors:
            messages.success(request, "Tu comentario se envió correctamente.")
            return redirect(reverse("mi_perfil") + "#comentarios-sugerencias")

    return _mostrar_perfil(request, form_comentario=form)


def _exigir_administrador(request):
    if not Perfil.objects.filter(user=request.user, rol__nombre="Administrador").exists():
        raise PermissionDenied


def _filtros_comentarios(datos):
    filtros = QueryDict(mutable=True)
    for clave, opciones in (
        ("estado", ("pendiente", "respondido", "revisado")),
        ("archivo", ("activos", "archivados", "todos")),
    ):
        valor = datos.get(clave, "")
        if valor in opciones:
            filtros[clave] = valor
    if filtros.get("estado") == "revisado":
        filtros["estado"] = "respondido"
    usuario = datos.get("usuario", "").strip()[:100]
    if usuario:
        filtros["usuario"] = usuario
    return filtros


def _volver_comentarios(request):
    datos = QueryDict(request.POST.get("filtros", ""))
    filtros = _filtros_comentarios(datos)
    pagina = datos.get("pagina", "")
    if pagina.isascii() and pagina.isdigit() and len(pagina) <= 10:
        filtros["pagina"] = pagina
    destino = reverse("admin_comentarios_sugerencias")
    return redirect(destino + ("?" + filtros.urlencode() if filtros else ""))


@login_required
def admin_comentarios_sugerencias(request):
    _exigir_administrador(request)
    filtros = _filtros_comentarios(request.GET)
    archivo = filtros.get("archivo", "activos")
    comentarios = ComentarioSugerencia.objects.select_related("usuario__perfil")
    if archivo != "todos":
        comentarios = comentarios.filter(archivado=archivo == "archivados")
    if filtros.get("estado") == "pendiente":
        comentarios = comentarios.filter(respuesta="")
    elif filtros.get("estado") == "respondido":
        comentarios = comentarios.exclude(respuesta="")
    if filtros.get("usuario"):
        comentarios = comentarios.filter(usuario__username__icontains=filtros["usuario"])
    comentarios = comentarios.annotate(
        orden_respuesta=models.Case(
            models.When(respuesta="", then=models.Value(0)),
            default=models.Value(1), output_field=models.IntegerField(),
        )
    )
    pagina = Paginator(comentarios.order_by("orden_respuesta", "-fecha_envio", "-pk"), 20).get_page(
        request.GET.get("pagina")
    )
    filtros_accion = filtros.copy()
    filtros_accion["pagina"] = pagina.number
    return render(request, "gestion/admin_comentarios.html", {
        "comentarios": pagina, "archivo": archivo,
        "estado": filtros.get("estado", ""),
        "usuario": filtros.get("usuario", ""),
        "filtros": filtros.urlencode(), "filtros_accion": filtros_accion.urlencode(),
    })


def _seleccion_comentarios(request, eliminar=False):
    form = (EliminarComentariosForm if eliminar else SeleccionComentariosForm)(request.POST)
    if not form.is_valid():
        for errores in form.errors.values():
            for error in errores:
                messages.error(request, error)
        return None
    return ComentarioSugerencia.objects.filter(pk__in=form.cleaned_data["ids"])


@login_required
@require_POST
def admin_eliminar_comentarios(request):
    _exigir_administrador(request)
    comentarios = _seleccion_comentarios(request, eliminar=True)
    if comentarios is not None:
        with transaction.atomic():
            seleccion = list(comentarios.select_for_update())
            if not seleccion:
                messages.error(request, "Los mensajes seleccionados ya no existen.")
            elif any(not comentario.archivado for comentario in seleccion):
                messages.error(request, "Archiva los mensajes antes de eliminarlos definitivamente.")
            else:
                cantidad, _ = comentarios.delete()
                messages.success(request, f"Se eliminaron definitivamente {cantidad} mensaje(s).")
    return _volver_comentarios(request)


def _actualizar_archivo_comentarios(request, archivado):
    comentarios = _seleccion_comentarios(request)
    if comentarios is not None:
        cantidad = comentarios.filter(archivado=not archivado).update(archivado=archivado)
        if cantidad:
            accion = "archivaron" if archivado else "restauraron"
            messages.success(request, f"Se {accion} {cantidad} mensaje(s).")
        else:
            messages.info(request, "No había mensajes disponibles para realizar esa acción.")
    return _volver_comentarios(request)


@login_required
@require_POST
def admin_archivar_comentarios(request):
    _exigir_administrador(request)
    return _actualizar_archivo_comentarios(request, True)


@login_required
@require_POST
def admin_restaurar_comentarios(request):
    _exigir_administrador(request)
    return _actualizar_archivo_comentarios(request, False)


@login_required
@require_POST
def admin_cambiar_estado_comentario(request, pk):
    _exigir_administrador(request)
    if pk > 9223372036854775807:
        raise Http404
    get_object_or_404(ComentarioSugerencia, pk=pk)
    filtros = QueryDict(mutable=True)
    filtros["filtros"] = request.POST.get("filtros", "")
    return redirect(reverse("admin_responder_comentario", args=[pk]) + "?" + filtros.urlencode())


@login_required
@require_http_methods(["GET", "POST"])
def admin_responder_comentario(request, pk):
    _exigir_administrador(request)
    if pk > 9223372036854775807:
        raise Http404
    comentario = get_object_or_404(
        ComentarioSugerencia.objects.select_related("usuario__perfil", "respondido_por"), pk=pk,
    )
    form = RespuestaComentarioForm(
        request.POST if request.method == "POST" else None, instance=comentario,
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            ComentarioSugerencia.objects.select_for_update().get(pk=comentario.pk)
            comentario = form.save(commit=False)
            comentario.respondido_por = request.user
            comentario.fecha_respuesta = timezone.now()
            comentario.revisado = True
            comentario.save(update_fields=["respuesta", "respondido_por", "fecha_respuesta", "revisado"])
        return _volver_comentarios(request)
    filtros = request.POST.get("filtros", "") if request.method == "POST" else request.GET.get("filtros", "")
    return render(request, "gestion/admin_responder_comentario.html", {
        "comentario": comentario, "form": form, "filtros_accion": filtros,
    })
