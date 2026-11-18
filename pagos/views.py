import logging

from uuid import uuid4
from django.db import OperationalError, IntegrityError, transaction
from django.http import HttpResponse
from datetime import timedelta
from django.utils import timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt

from torneo.models import Inscripcion

from .models import Pago, Venta
from .conciliacion import consultar_pago_webpay
from .services import obtener_o_crear_venta, registrar_resultado_webpay
from .webpay import crear_transaccion_webpay, confirmar_transaccion_webpay, obtener_cliente_webpay


@login_required
def resumen_pago(request, inscripcion_id):
    inscripcion = get_object_or_404(
        Inscripcion.objects.select_related(
            "inscripcion_torneo",
            "inscripcion_usuario",
        ),
        pk=inscripcion_id,
        inscripcion_usuario=request.user,
    )

    if inscripcion.inscripcion_estado != "Pendiente":
        messages.warning(
            request,
            "Esta inscripción no está pendiente de pago.",
        )
        return redirect("listar_torneos")

    try:
        venta = obtener_o_crear_venta(inscripcion.id)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("listar_torneos")

    return render(
        request,
        "pagos/resumen.html",
        {
            "inscripcion": inscripcion,
            "torneo": inscripcion.inscripcion_torneo,
            "venta": venta,
            "detalle": venta.detalle,
        },
    )



@login_required
@require_POST
def iniciar_pago_webpay(request, inscripcion_id):

    inscripcion = get_object_or_404(
        Inscripcion,
        pk=inscripcion_id,
        inscripcion_usuario=request.user,
    )

    try:
        venta = obtener_o_crear_venta(inscripcion.id)
    except ValidationError as error:
        messages.error(
            request,
            "; ".join(error.messages),
        )
        return redirect("listar_torneos")

    if venta.venta_estado != "Pendiente":
        messages.warning(
            request,
            "Esta inscripción ya no está pendiente de pago.",
        )
        return redirect("listar_torneos")

        # Comprobar los cupos antes de iniciar
        # una nueva transacción en Transbank.
    torneo = inscripcion.inscripcion_torneo
    torneo.refresh_from_db()

    if torneo.torneo_estado != "Publicado":
        messages.error(
            request,
            "Este torneo ya no está disponible "
            "para inscripciones.",
        )
        return redirect(
            "resumen_pago",
            inscripcion_id=inscripcion.id,
        )

    if (
        torneo.torneo_cuposOcupados
        >= torneo.torneo_cupoMaximo
    ):
        messages.error(
            request,
            "Este torneo ya no tiene cupos "
            "disponibles. No se iniciará "
            "ningún cobro.",
        )
        return redirect(
            "resumen_pago",
            inscripcion_id=inscripcion.id,
        )

    

    if venta.venta_total <= 0:
        messages.error(
            request,
            "El monto de la venta no es válido.",
        )
        return redirect(
            "resumen_pago",
            inscripcion_id=inscripcion.id,
        )

    # Revisar TODOS los intentos abiertos,
    # incluidos los que están en Revision.
    pagos_abiertos = list(
        Pago.objects.filter(
            pago_venta=venta,
            pago_estado__in=[
                "Pendiente",
                "Revision",
                "Incidencia",
            ],
        ).order_by("id")
    )

    for pago_anterior in pagos_abiertos:

        # Conciliar antes de decidir si podemos
        # iniciar una transacción nueva.
        resultado = consultar_pago_webpay(
            pago_anterior.id
        )

        pago_anterior.refresh_from_db()

        # Si se recuperó un pago aprobado,
        # no debemos realizar otro cobro.
        if pago_anterior.pago_estado == "Aprobado":
            messages.success(
                request,
                "Tu pago ya fue aprobado y "
                "la inscripción fue confirmada.",
            )
            return redirect("listar_torneos")

        # Los intentos definitivamente rechazados
        # no impiden que el jugador vuelva a pagar.
        if pago_anterior.pago_estado in (
            "Rechazado",
            "Anulado",
            "Expirado",
        ):
            continue

        # Todavía no existe evidencia suficiente
        # para iniciar otro cobro.
        if resultado.get("resultado") == "INITIALIZED":
            mensaje = (
                "Tu intento anterior sigue sin completar "
                "en Transbank. Estamos verificando su "
                "resultado antes de permitir otro pago."
            )
        else:
            mensaje = (
                "Hay un intento de pago que necesita "
                "verificación. No iniciaremos otro cobro "
                "hasta resolverlo."
            )

        messages.warning(request, mensaje)

        return redirect(
            "resumen_pago",
            inscripcion_id=inscripcion.id,
        )

    # Volver a validar antes de crear el nuevo intento.
    # select_for_update aporta bloqueo real en bases
    # compatibles, como PostgreSQL.
    
    # Crear el intento de forma protegida.
    try:
        with transaction.atomic():

            venta_actual = (
                Venta.objects
                .select_for_update()
                .get(pk=venta.pk)
            )

            if venta_actual.venta_estado != "Pendiente":
                messages.warning(
                    request,
                    "Esta venta ya no está pendiente.",
                )
                return redirect("listar_torneos")

            # Comprobar tanto Pendiente como Revision.
            if Pago.objects.filter(
                pago_venta=venta_actual,
                pago_estado__in=[
                    "Pendiente",
                    "Revision",
                    "Incidencia",
                ],
            ).exists():

                messages.warning(
                    request,
                    "Ya existe un intento de pago "
                    "en proceso o en revisión.",
                )

                return redirect(
                    "resumen_pago",
                    inscripcion_id=inscripcion.id,
                )

            orden_compra = (
                f"MC-{venta_actual.pk}-{uuid4().hex[:12]}"
            )

            pago = Pago.objects.create(
                pago_venta=venta_actual,
                pago_monto=venta_actual.venta_total,
                pago_estado="Pendiente",
                pago_metodo="Webpay",
                pago_orden_compra=orden_compra,
                pago_revisar_desde=(
                    timezone.now()
                    + timedelta(minutes=5)
                ),
            )

    except IntegrityError:
        # La base de datos impidió crear
        # un intento duplicado.
        messages.warning(
            request,
            "Ya se está procesando otro intento "
            "de pago para esta inscripción.",
        )

        return redirect(
            "resumen_pago",
            inscripcion_id=inscripcion.id,
        )

    except OperationalError:
        # SQLite puede estar ocupado si varias
        # solicitudes intentan escribir a la vez.
        messages.error(
            request,
            "El sistema de pagos está ocupado. "
            "Vuelve a intentarlo en unos momentos.",
        )

        return redirect(
            "resumen_pago",
            inscripcion_id=inscripcion.id,
        )


    url_retorno = request.build_absolute_uri(
        reverse("retorno_webpay")
    )

    try:
        respuesta = crear_transaccion_webpay(
            orden_compra=orden_compra,
            sesion_id=f"MC-{request.user.pk}-{pago.pk}",
            monto=venta_actual.venta_total,
            url_retorno=url_retorno,
        )

        token = respuesta["token"]
        url_webpay = respuesta["url"]

        pago.pago_token = token
        pago.save(
            update_fields=["pago_token"]
        )

    except Exception:
        # No sabemos si Transbank alcanzó a crear
        # la transacción. Conservamos el registro.
        pago.pago_estado = "Revision"
        pago.save(
            update_fields=["pago_estado"]
        )

        messages.error(
            request,
            "No fue posible iniciar Webpay. "
            "El intento quedó registrado para revisión.",
        )
        return redirect(
            "resumen_pago",
            inscripcion_id=inscripcion.id,
        )

    # Usamos siempre la URL y el token NUEVOS
    # entregados por Transbank.
    return render(
        request,
        "pagos/redirect_webpay.html",
        {
            "url_webpay": url_webpay,
            "token": token,
        },
    )



@csrf_exempt
@require_http_methods(["GET", "POST"])
def retorno_webpay(request):
    """
    Procesa el retorno de Webpay Plus.

    - token_ws: retorno normal.
    - TBK_TOKEN: cancelación o retorno especial.
    - TBK_ORDEN_COMPRA y TBK_ID_SESION:
      retorno por timeout u otra interrupción.

    Evita ejecutar commit() repetidamente.
    """

    logger = logging.getLogger(__name__)

    def mostrar_resultado(pago, mensaje, exitoso=False):
        return render(
            request,
            "pagos/resultado_webpay.html",
            {
                "pago": pago,
                "mensaje": mensaje,
                "exitoso": exitoso,
            },
        )

    # Aceptar los parámetros enviados por
    # Transbank tanto en GET como en POST.
    datos = request.POST if request.method == "POST" else request.GET

    token_ws = datos.get("token_ws")
    tbk_token = datos.get("TBK_TOKEN")
    orden_retorno = datos.get("TBK_ORDEN_COMPRA")
    sesion_retorno = datos.get("TBK_ID_SESION")

    # Un retorno puede traer datos del flujo normal
    # o de cancelación/interrupción.
    token = tbk_token or token_ws

    if token:
        pago = (
            Pago.objects
            .select_related("pago_venta")
            .filter(pago_token=token)
            .first()
        )
    elif orden_retorno:
        pago = (
            Pago.objects
            .select_related("pago_venta")
            .filter(pago_orden_compra=orden_retorno)
            .first()
        )
    else:
        return mostrar_resultado(
            None,
            "No recibimos datos suficientes "
            "para identificar la transacción.",
        )

    if pago is None:
        return mostrar_resultado(
            None,
            "La transacción no existe en Mundo Cartas.",
        )

    # Validar los datos adicionales del retorno.
    if (
        orden_retorno
        and orden_retorno != pago.pago_orden_compra
    ):
        return mostrar_resultado(
            None,
            "Los datos de la transacción no coinciden.",
        )

    sesion_esperada = (
        f"MC-{pago.pago_venta.venta_usuario_id}-{pago.pk}"
    )

    if (
        sesion_retorno
        and sesion_retorno != sesion_esperada
    ):
        return mostrar_resultado(
            None,
            "La sesión de pago no coincide.",
        )

    # Si ya fue aprobado, mostrar el resultado
    # sin volver a confirmar en Transbank.
    if pago.pago_estado == "Aprobado":
        return mostrar_resultado(
            pago,
            "¡Pago aprobado! Tu inscripción "
            "fue confirmada.",
            True,
        )

    # Los pagos que ya tienen un resultado
    # negativo definitivo no se confirman otra vez.
    if pago.pago_estado in (
        "Rechazado",
        "Anulado",
    ):
        return mostrar_resultado(
            pago,
            "El pago no fue aprobado.",
        )

    # CANCELACIÓN, TIMEOUT O RETORNO ESPECIAL:
    # no ejecutar commit().
    retorno_especial = bool(
        tbk_token
        or orden_retorno
        or sesion_retorno
    )

    if retorno_especial:
        try:
            consultar_pago_webpay(pago.id)
        except Exception:
            logger.exception(
                "Error consultando retorno especial "
                "de Webpay, pago %s",
                pago.id,
            )

        pago.refresh_from_db()

        if pago.pago_estado == "Aprobado":
            return mostrar_resultado(
                pago,
                "El pago fue verificado y "
                "la inscripción está confirmada.",
                True,
            )

        return mostrar_resultado(
            pago,
            "La operación fue cancelada o "
            "interrumpida. No se ha confirmado "
            "un nuevo pago. Puedes consultar "
            "el estado desde Mundo Cartas.",
        )

    # A partir de aquí debe existir token_ws.
    if not token_ws:
        return mostrar_resultado(
            pago,
            "No recibimos el token necesario "
            "para confirmar la transacción.",
        )

    # Si la venta ya está pagada por otro intento,
    # no ejecutar un segundo commit().
    if pago.pago_venta.venta_estado != "Pendiente":
        try:
            consultar_pago_webpay(pago.id)
        except Exception:
            logger.exception(
                "Error verificando un retorno tardío "
                "del pago %s",
                pago.id,
            )

        pago.refresh_from_db()

        return mostrar_resultado(
            pago,
            "Esta venta ya tiene un resultado. "
            "No realizaremos otra confirmación. "
            "El intento se revisará por seguridad.",
            pago.pago_estado == "Aprobado",
        )

    # Si un intento expirado tiene otro intento
    # posterior, no confirmar el antiguo.
    if pago.pago_estado == "Expirado":
        existe_intento_posterior = (
            Pago.objects.filter(
                pago_venta=pago.pago_venta,
                pago_fecha__gt=pago.pago_fecha,
            )
            .exclude(pk=pago.pk)
            .exists()
        )

        if existe_intento_posterior:
            try:
                consultar_pago_webpay(pago.id)
            except Exception:
                logger.exception(
                    "Error verificando pago antiguo %s",
                    pago.id,
                )

            return mostrar_resultado(
                pago,
                "Este intento fue reemplazado por "
                "otro más reciente. Su resultado "
                "requiere verificación.",
            )

    # Reclamar el derecho a ejecutar commit().
    # Esta actualización es una sola operación
    # en la base de datos.
    ahora = timezone.now()

    actualizado = Pago.objects.filter(
        pk=pago.id,
        pago_commit_iniciado_en__isnull=True,
        pago_estado__in=[
            "Pendiente",
            "Revision",
            "Expirado",
        ],
        pago_venta__venta_estado="Pendiente",
    ).update(
        pago_commit_iniciado_en=ahora,
    )

    # Otro retorno ya inició la confirmación.
    if actualizado != 1:
        try:
            consultar_pago_webpay(pago.id)
        except Exception:
            logger.exception(
                "Error recuperando el pago %s",
                pago.id,
            )

        pago.refresh_from_db()

        if pago.pago_estado == "Aprobado":
            return mostrar_resultado(
                pago,
                "¡Pago aprobado! Tu inscripción "
                "está confirmada.",
                True,
            )

        return mostrar_resultado(
            pago,
            "Esta transacción ya está siendo "
            "procesada o necesita conciliación. "
            "No se realizará otro cobro.",
        )

    # Confirmar la transacción una sola vez.
    try:
        respuesta = confirmar_transaccion_webpay(
            token_ws
        )

        resultado = registrar_resultado_webpay(
            pago.id,
            respuesta,
        )

    except Exception:
        logger.exception(
            "Error confirmando el pago %s",
            pago.id,
        )

        # Si commit() se ejecutó en Transbank
        # pero Django falló, recuperar mediante
        # status(), sin llamar commit() nuevamente.
        try:
            consultar_pago_webpay(pago.id)
        except Exception:
            logger.exception(
                "No fue posible recuperar el pago %s",
                pago.id,
            )

        pago.refresh_from_db()

        if pago.pago_estado == "Aprobado":
            return mostrar_resultado(
                pago,
                "¡Pago aprobado! Tu inscripción "
                "fue confirmada.",
                True,
            )

        return mostrar_resultado(
            pago,
            "No pudimos completar la verificación "
            "del pago. La operación quedó registrada "
            "para conciliación. No vuelvas a pagar "
            "hasta conocer su resultado.",
        )

    pago.refresh_from_db()

    if resultado is True:
        return mostrar_resultado(
            pago,
            "¡Pago aprobado! Tu inscripción "
            "fue confirmada.",
            True,
        )

    if resultado is False:
        return mostrar_resultado(
            pago,
            "El pago no fue aprobado. "
            "Podrás intentar nuevamente "
            "cuando corresponda.",
        )

    return mostrar_resultado(
        pago,
        "La transacción necesita verificación. "
        "No realizaremos otro cobro mientras "
        "el resultado siga pendiente.",
    )

