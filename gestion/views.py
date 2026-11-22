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
from registro.forms import PerfilUsuarioForm
from django.contrib import messages
from django.views.decorators.http import require_http_methods , require_POST

from .forms import ComentarioSugerenciaForm

from django.core.exceptions import PermissionDenied
from .models import ComentarioSugerencia

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
        "form": form,
        "editar_perfil": request.method == "POST" or request.GET.get("editar") == "1",
        "torneos_inscritos": torneos_inscritos,
        "historial_reciente": historial_reciente,
        "puntos_por_juego": puntos_por_juego,
    })

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
    # Verificar que el usuario tenga el rol de Jugador.
    es_jugador = Perfil.objects.filter(
        user=request.user,
        rol__nombre="Jugador"
    ).exists()

    if not es_jugador:
        messages.error(
            request,
            "Solo los jugadores pueden enviar comentarios o sugerencias."
        )
        return redirect("mi_perfil")

    # Recibir y validar los datos enviados.
    form = ComentarioSugerenciaForm(request.POST)

    if form.is_valid():
        comentario = form.save(commit=False)

        # Asociar el mensaje al jugador que inició sesión.
        comentario.usuario = request.user
        comentario.save()

        messages.success(
            request,
            "Tu comentario o sugerencia se envió correctamente."
        )
    else:
        messages.error(
            request,
            "No se pudo enviar el mensaje. Verifica que tenga contenido "
            "y no supere los 500 caracteres."
        )

    return redirect("mi_perfil")

@login_required
def admin_comentarios_sugerencias(request):
    
    es_administrador = Perfil.objects.filter(
        user=request.user,
        rol__nombre="Administrador"
    ).exists()

    if not es_administrador:
        raise PermissionDenied

    
    comentarios = ComentarioSugerencia.objects.select_related(
        "usuario"
    ).order_by("revisado", "-fecha_envio")

    return render(
        request,
        "gestion/admin_comentarios.html",
        {
            "comentarios": comentarios,
        }
    )

@login_required
@require_POST
def admin_eliminar_comentarios(request):

    
    es_administrador = Perfil.objects.filter(
        user=request.user,
        rol__nombre="Administrador"
    ).exists()

    if not es_administrador:
        raise PermissionDenied

    
    ids_recibidos = request.POST.getlist("ids")

    ids_validos = []

    for valor in ids_recibidos:
        try:
            identificador = int(valor)

            if identificador > 0:
                ids_validos.append(identificador)

        except (ValueError, TypeError):
            continue

    if not ids_validos:
        messages.error(
            request,
            "Debes seleccionar al menos un comentario."
        )
        return redirect("admin_comentarios_sugerencias")

    
    comentarios = ComentarioSugerencia.objects.filter(
        id__in=ids_validos
    )

    cantidad = comentarios.count()

   
    comentarios.delete()

    if cantidad == 1:
        messages.success(
            request,
            "El comentario se eliminó correctamente."
        )
    else:
        messages.success(
            request,
            f"Se eliminaron {cantidad} comentarios correctamente."
        )

    return redirect("admin_comentarios_sugerencias")

@login_required
@require_POST
def admin_cambiar_estado_comentario(request, pk):

    
    es_administrador = Perfil.objects.filter(
        user=request.user,
        rol__nombre="Administrador"
    ).exists()

    if not es_administrador:
        raise PermissionDenied

    
    comentario = get_object_or_404(
        ComentarioSugerencia,
        pk=pk
    )

    
    estado = request.POST.get("estado")

    if estado not in ["pendiente", "revisado"]:
        messages.error(
            request,
            "El estado seleccionado no es válido."
        )
        return redirect("admin_comentarios_sugerencias")

    
    comentario.revisado = estado == "revisado"

    comentario.save(update_fields=["revisado"])

    messages.success(
        request,
        "El estado del comentario se actualizó correctamente."
    )

    return redirect("admin_comentarios_sugerencias")
