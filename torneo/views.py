
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.db.models.deletion import ProtectedError, RestrictedError
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_http_methods, require_POST

from registro.models import Perfil

from .forms import ConfirmarEliminarTorneoForm, JuegoForm, TorneoForm, ResultadoTorneoForm
from .models import Inscripcion, Juego, Torneo, ResultadoTorneo, ReglaPuntuacionTorneo, Liga
from .presentacion import normalizar_nombre
from .services import obtener_clasificacion_liga


# DECORADOR: SOLO ADMINISTRADORES
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


# SOLICITAR INSCRIPCIÓN A UN TORNEO

@login_required
@require_POST
def solicitar_inscripcion(request, pk):

    torneo = get_object_or_404(Torneo, pk=pk)

    # Verificar que el usuario sea jugador.
    es_jugador = Perfil.objects.filter(
        user=request.user,
        rol__nombre="Jugador"
    ).exists()

    if not es_jugador:
        messages.error(
            request,
            "Solo los jugadores pueden inscribirse en torneos."
        )
        return redirect("listar_torneos")

    # Buscar si el jugador ya tiene una inscripción.
    inscripcion_existente = Inscripcion.objects.filter(
        inscripcion_usuario=request.user,
        inscripcion_torneo=torneo
    ).first()

    if inscripcion_existente is not None:

        # Si está pendiente, permitir continuar al pago.
        if inscripcion_existente.inscripcion_estado == "Pendiente":
            return redirect(
                "resumen_pago",
                inscripcion_id=inscripcion_existente.pk
            )

        # Si ya está confirmada, no volver a cobrar.
        if inscripcion_existente.inscripcion_estado == "Confirmada":
            messages.info(
                request,
                "Ya estás inscrito en este torneo."
            )
            return redirect("listar_torneos")

        messages.warning(
            request,
            "Esta inscripción está cancelada. "
            "No puedes generar otra automáticamente."
        )
        return redirect("listar_torneos")

    # Validar que el torneo esté publicado.
    if torneo.torneo_estado != "Publicado":
        messages.error(
            request,
            "Este torneo no está disponible para inscripciones."
        )
        return redirect("listar_torneos")

    # Validar los cupos.
    if torneo.cupos_disponibles <= 0:
        messages.error(
            request,
            "Este torneo no tiene cupos disponibles."
        )
        return redirect("listar_torneos")

    # El proyecto utiliza pesos chilenos enteros.

    # Obtener el precio del torneo.
    precio = torneo.torneo_precio

    # Validar que el precio sea un número entero.
    # Funciona tanto con int como con Decimal.
    if precio != int(precio):
        messages.error(
            request,
            "El precio del torneo debe ser un número entero."
        )
        return redirect("listar_torneos")

    # Convertir el precio a pesos chilenos enteros.
    precio = int(precio)


    try:
        with transaction.atomic():

            inscripcion = Inscripcion.objects.create(
                inscripcion_usuario=request.user,
                inscripcion_torneo=torneo,
                inscripcion_estado="Pendiente",
                inscripcion_precio=int(precio)
            )

    except IntegrityError:

        # Puede ocurrir si dos solicitudes intentan
        # crear la misma inscripción al mismo tiempo.
        inscripcion = Inscripcion.objects.filter(
            inscripcion_usuario=request.user,
            inscripcion_torneo=torneo
        ).first()

        if (
            inscripcion is not None
            and inscripcion.inscripcion_estado == "Pendiente"
        ):
            return redirect(
                "resumen_pago",
                inscripcion_id=inscripcion.pk
            )

        messages.warning(
            request,
            "No fue posible crear la inscripción."
        )
        return redirect("listar_torneos")

    # Llevar directamente al resumen de pago.
    return redirect(
        "resumen_pago",
        inscripcion_id=inscripcion.pk
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


# CANCELAR TORNEO
@administrador_requerido
@require_http_methods(["GET", "POST"])
def admin_cancelar_torneo(request, pk):
    torneo = get_object_or_404(Torneo, pk=pk)

    if request.method == "POST":
        if torneo.torneo_estado != "Cancelado":
            torneo.torneo_estado = "Cancelado"
            torneo.save(update_fields=["torneo_estado"])

            messages.success(
                request,
                "Torneo cancelado. Se conserva su historial."
            )
        else:
            messages.info(
                request,
                "El torneo ya estaba cancelado."
            )

        return redirect("admin_listar_torneos")

    return render(
        request,
        "torneo/admin_cancelar.html",
        {"torneo": torneo}
    )


# ELIMINAR TORNEO DEFINITIVAMENTE
@administrador_requerido
@require_http_methods(["GET", "POST"])
def admin_eliminar_torneo(request, pk):
    torneo = get_object_or_404(Torneo, pk=pk)

    form = ConfirmarEliminarTorneoForm(
        request.POST if request.method == "POST" else None
    )

    estado_respuesta = 200

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    torneo.delete()

            except (ProtectedError, RestrictedError):
                form.add_error(
                    None,
                    "No se puede eliminar porque existen registros "
                    "relacionados. Puedes cancelar el torneo para conservarlos."
                )
                estado_respuesta = 409

            else:
                messages.success(
                    request,
                    "Torneo eliminado definitivamente."
                )
                return redirect("admin_listar_torneos")

        else:
            estado_respuesta = 400

    return render(
        request,
        "torneo/admin_eliminar.html",
        {
            "torneo": torneo,
            "form": form,
        },
        status=estado_respuesta
    )


# LISTAR JUEGOS
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
        juegos = juegos.filter(
            juego_activo=(estado == "activos")
        )

    filtro = normalizar_nombre(busqueda)

    juegos = [
        juego for juego in juegos
        if not filtro
        or filtro in normalizar_nombre(juego.juego_nombre)
    ]

    return render(
        request,
        "torneo/admin_juegos.html",
        {
            "juegos": juegos,
            "busqueda": busqueda,
            "estado": estado,
            "total": len(juegos),
        }
    )


# CREAR JUEGO
@administrador_requerido
@require_http_methods(["GET", "POST"])
def admin_crear_juego(request):
    form = JuegoForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None
    )

    if request.method == "POST" and form.is_valid():
        form.save()

        messages.success(
            request,
            "Juego creado correctamente."
        )

        return redirect("admin_listar_juegos")

    return render(
        request,
        "torneo/admin_juego_formulario.html",
        {
            "form": form,
            "titulo": "Crear juego",
            "texto_boton": "Crear juego",
        }
    )


# ACTUALIZAR JUEGO
@administrador_requerido
@require_http_methods(["GET", "POST"])
def admin_actualizar_juego(request, pk):
    juego = get_object_or_404(Juego, pk=pk)

    form = JuegoForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        instance=juego
    )

    if request.method == "POST" and form.is_valid():
        form.save()

        messages.success(
            request,
            "Juego actualizado correctamente."
        )

        return redirect("admin_listar_juegos")

    return render(
        request,
        "torneo/admin_juego_formulario.html",
        {
            "form": form,
            "juego": juego,
            "titulo": "Editar juego",
            "texto_boton": "Guardar cambios",
        }
    )


# DESACTIVAR JUEGO
@administrador_requerido
@require_http_methods(["GET", "POST"])
def admin_desactivar_juego(request, pk):
    juego = get_object_or_404(Juego, pk=pk)

    if request.method == "POST":
        if juego.juego_activo:
            juego.juego_activo = False
            juego.save(update_fields=["juego_activo"])

            messages.success(
                request,
                "Juego desactivado. Sus torneos y ligas se conservan."
            )

        return redirect("admin_listar_juegos")

    return render(
        request,
        "torneo/admin_juego_desactivar.html",
        {"juego": juego}
    )


@administrador_requerido
def admin_resultados_torneos(request):
    torneos = (
        Torneo.objects
        .select_related("torneo_juego", "torneo_liga")
        .order_by("-torneo_inicio")
    )
    ligas = (
        Liga.objects
        .select_related("liga_juego")
        .order_by("liga_nombre")
    )

    return render(request, "torneo/admin_resultados.html", {
        "torneos": torneos,
        "ligas": ligas,
    })

@administrador_requerido
def admin_resultados_detalle(request, pk):
    torneo = get_object_or_404(Torneo, pk=pk)

    inscripciones = (
        Inscripcion.objects
        .filter(
            inscripcion_torneo=torneo,
            inscripcion_estado="Confirmada",
        )
        .select_related("inscripcion_usuario", "resultado_torneo_nuevo")
        .order_by("inscripcion_usuario__username")
    )

    regla = ReglaPuntuacionTorneo.objects.filter(
        nombre="Puntuación estándar"
    ).first()

    for inscripcion in inscripciones:
        inscripcion.puntos_torneo = None

        resultado = getattr(
            inscripcion,
            "resultado_torneo_nuevo",
            None
        )

        if resultado is not None and resultado.participo and regla is not None:
            inscripcion.puntos_torneo = resultado.calcular_puntos_torneo(regla)
    return render(request, "torneo/admin_resultados_detalle.html", {
        "torneo": torneo,
        "inscripciones": inscripciones,
    })


@administrador_requerido
@require_http_methods(["GET", "POST"])
def admin_registrar_resultado(request, pk, inscripcion_id):
    torneo = get_object_or_404(
        Torneo,
        pk=pk,
        torneo_estado="Finalizado",
    )

    inscripcion = get_object_or_404(
        Inscripcion,
        pk=inscripcion_id,
        inscripcion_torneo=torneo,
        inscripcion_estado="Confirmada",
    )

    resultado = ResultadoTorneo.objects.filter(
        inscripcion=inscripcion
    ).first()

    form = ResultadoTorneoForm(
        request.POST if request.method == "POST" else None,
        instance=resultado,
    )

    if request.method == "POST" and form.is_valid():
        resultado = form.save(commit=False)
        resultado.inscripcion = inscripcion
        resultado.save()

        messages.success(
            request,
            "Resultado guardado correctamente.",
        )

        return redirect("admin_resultados_detalle", pk=torneo.pk)

    return render(request, "torneo/admin_resultado_form.html", {
        "torneo": torneo,
        "inscripcion": inscripcion,
        "form": form,
    })


@administrador_requerido
def admin_clasificacion_liga(request, pk):
    liga = get_object_or_404(Liga, pk=pk)

    clasificacion = obtener_clasificacion_liga(liga)

    return render(
        request,
        "torneo/admin_clasificacion_liga.html",
        {
            "liga": liga,
            "clasificacion": clasificacion,
        }
    )
