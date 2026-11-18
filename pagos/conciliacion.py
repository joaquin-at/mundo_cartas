
import logging
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Pago
from .services import registrar_resultado_webpay
from .webpay import obtener_cliente_webpay


logger = logging.getLogger(__name__)

INTERVALO_REVISION = timedelta(minutes=5)
INTERVALO_EXPIRADOS = timedelta(hours=1)
VENTANA_CONSULTA = timedelta(days=7)



def marcar_pago_para_revision(pago_id):
    """
    Programa una nueva consulta sin perder
    el estado importante del pago.
    """

    with transaction.atomic():

        pago = (
            Pago.objects
            .select_for_update()
            .get(pk=pago_id)
        )

        if pago.pago_estado not in (
            "Pendiente",
            "Revision",
            "Expirado",
            "Incidencia",
        ):
            return

        ahora = timezone.now()

        pago.pago_ultima_verificacion = ahora

        if pago.pago_estado == "Expirado":
            intervalo = INTERVALO_EXPIRADOS
        else:
            intervalo = INTERVALO_REVISION

        pago.pago_revisar_desde = ahora + intervalo

        campos = [
            "pago_ultima_verificacion",
            "pago_revisar_desde",
        ]

        # Solo Pendiente pasa a Revision.
        # Incidencia y Expirado conservan su estado.
        if pago.pago_estado == "Pendiente":
            pago.pago_estado = "Revision"
            campos.append("pago_estado")

        pago.save(update_fields=campos)



def puede_expirar_intento(pago):
    """
    Determina si un intento INITIALIZED puede
    cerrarse localmente por abandono.

    Esta política solo se habilita expresamente
    para el ambiente de integración.
    """
    # Si ya intentamos confirmar el pago, no
    # podemos declararlo expirado solo por tiempo.
    # Debemos recuperar su resultado de Transbank.
    if pago.pago_commit_iniciado_en is not None:
        return False
    
    habilitado = (
        settings.DEBUG
        and getattr(
            settings,
            "WEBPAY_PERMITIR_REINTENTOS_TEST",
            False,
        )
    )

    if not habilitado:
        return False

    minutos = getattr(
        settings,
        "WEBPAY_MINUTOS_PARA_EXPIRAR",
        30,
    )

    antiguedad = timezone.now() - pago.pago_fecha

    return antiguedad >= timedelta(
        minutes=minutos
    )


def consultar_pago_webpay(pago_id):
    """
    Consulta y concilia un intento de Webpay.

    Nunca ejecuta commit() nuevamente.
    Nunca reutiliza un token para pagar.

    Un intento antiguo en INITIALIZED puede
    quedar Expirado en el entorno de pruebas,
    únicamente después de consultar Transbank.
    """

    pago = Pago.objects.get(pk=pago_id)

    # Estos estados ya están cerrados.
    if pago.pago_estado in (
        "Aprobado",
        "Rechazado",
        "Anulado",
    ):
        return {
            "resultado": "cerrado",
            "mensaje": "El pago ya está cerrado.",
            "pago_id": pago_id,
            "estado_local": pago.pago_estado,
        }

    # No es seguro cerrar automáticamente
    # un intento que nunca recibió token.
    if not pago.pago_token:
        marcar_pago_para_revision(pago_id)

        return {
            "resultado": "sin_token",
            "mensaje": (
                "El intento no tiene token y "
                "permanece en revisión."
            ),
            "pago_id": pago_id,
            "estado_local": "Revision",
        }

    # Primero consultamos el estado real.
    try:
        respuesta = obtener_cliente_webpay().status(
            pago.pago_token
        )

    except Exception:
        logger.exception(
            "Error consultando pago %s en Transbank",
            pago_id,
        )

        marcar_pago_para_revision(pago_id)

        return {
            "resultado": "error_consulta",
            "mensaje": (
                "No se pudo consultar Transbank. "
                "El pago necesita revisión."
            ),
            "pago_id": pago_id,
            "estado_local": Pago.objects.get(
                pk=pago_id
            ).pago_estado,
        }

    estado_transbank = respuesta.get(
        "status",
        "",
    )

    # Usar la misma lógica central que procesa
    # autorizaciones, ventas e inscripciones.
    try:
        resultado_registro = registrar_resultado_webpay(
            pago_id,
            respuesta,
        )

    except ValidationError as error:
        marcar_pago_para_revision(pago_id)

        return {
            "resultado": "error_validacion",
            "mensaje": "; ".join(error.messages),
            "pago_id": pago_id,
            "estado_transbank": estado_transbank,
            "estado_local": Pago.objects.get(
                pk=pago_id
            ).pago_estado,
        }

    except Exception:
        logger.exception(
            "Error conciliando pago %s",
            pago_id,
        )

        marcar_pago_para_revision(pago_id)

        return {
            "resultado": "error_conciliacion",
            "mensaje": (
                "No se pudo completar la conciliación."
            ),
            "pago_id": pago_id,
            "estado_transbank": estado_transbank,
            "estado_local": Pago.objects.get(
                pk=pago_id
            ).pago_estado,
        }

    pago.refresh_from_db()
    ahora = timezone.now()

    # Si Transbank sigue en INITIALIZED y ya
    # pasó el margen configurado, podemos
    # cerrar localmente el intento de prueba.
    if (
        estado_transbank == "INITIALIZED"
        and puede_expirar_intento(pago)
    ):
        Pago.objects.filter(
            pk=pago_id,
            pago_token=pago.pago_token,
            pago_estado__in=[
                "Pendiente",
                "Revision",
                "Expirado",
            ],
            pago_estado_transbank="INITIALIZED",
        ).update(
            pago_estado="Expirado",
            pago_revisar_desde=(
                ahora + INTERVALO_EXPIRADOS
            ),
        )

    # Programar la próxima consulta.
    pago.refresh_from_db()

    if pago.pago_estado in (
        "Pendiente",
        "Revision",
        "Incidencia",
    ):
        Pago.objects.filter(
            pk=pago_id,
            pago_estado__in=["Pendiente", "Revision", "Incidencia",],
        ).update(
            pago_revisar_desde=(
                ahora + INTERVALO_REVISION
            )
        )

    elif pago.pago_estado == "Expirado":
        Pago.objects.filter(
            pk=pago_id,
            pago_estado="Expirado",
        ).update(
            pago_revisar_desde=(
                ahora + INTERVALO_EXPIRADOS
            )
        )

    pago.refresh_from_db()

    return {
        "resultado": estado_transbank,
        "mensaje": "Consulta y conciliación realizadas.",
        "pago_id": pago_id,
        "estado_local": pago.pago_estado,
        "inscripcion_confirmada": (
            resultado_registro is True
        ),
    }



def revisar_pagos_pendientes():
    """
    Consulta pagos pendientes, en revisión,
    con incidencias y expirados recientes.

    Los pagos antiguos que ya no puedan
    consultarse seguirán visibles en auditoría.
    """

    ahora = timezone.now()

    pagos = (
        Pago.objects
        .filter(
            Q(
                pago_estado__in=[
                    "Pendiente",
                    "Revision",
                    "Incidencia",
                ]
            )
            |
            Q(
                pago_estado="Expirado",
            )
        )
        .filter(
            pago_fecha__gte=(
                ahora - VENTANA_CONSULTA
            )
        )
        .filter(
            Q(pago_revisar_desde__isnull=True)
            |
            Q(pago_revisar_desde__lte=ahora)
        )
        .order_by("pago_fecha")
    )

    ids_pagos = list(
        pagos.values_list("id", flat=True)
    )

    resultados = []

    for pago_id in ids_pagos:
        resultado = consultar_pago_webpay(pago_id)
        resultados.append(resultado)

    return resultados
