
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from torneo.models import Inscripcion, Torneo

from .models import Venta, DetalleVenta, Pago



#  OBTENER O CREAR UNA VENTA

def obtener_o_crear_venta(inscripcion_id):
    """
    Obtiene la venta de una inscripción pendiente.

    Si no existe, crea una venta y su detalle.
    Si ya existe, reutiliza la misma venta.
    """

    with transaction.atomic():

        inscripcion = (
            Inscripcion.objects
            .select_for_update()
            .select_related("inscripcion_torneo")
            .get(pk=inscripcion_id)
        )

        # La inscripción debe estar pendiente.
        if inscripcion.inscripcion_estado != "Pendiente":
            raise ValidationError(
                "La inscripción no está pendiente de pago."
            )

        # Comprobar si ya tiene una venta.
        detalle = (
            DetalleVenta.objects
            .select_related("detalle_venta")
            .filter(detalle_inscripcion=inscripcion)
            .first()
        )

        if detalle is not None:
            return detalle.detalle_venta

        # Comprobar disponibilidad del torneo.
        torneo = inscripcion.inscripcion_torneo

        if torneo.torneo_estado != "Publicado":
            raise ValidationError(
                "El torneo ya no está disponible."
            )

        if torneo.cupos_disponibles <= 0:
            raise ValidationError(
                "El torneo no tiene cupos disponibles."
            )

        # Precio guardado cuando el jugador se inscribió.
        precio = inscripcion.inscripcion_precio

        # Crear venta pendiente.
        venta = Venta.objects.create(
            venta_usuario=inscripcion.inscripcion_usuario,
            venta_total=precio,
            venta_estado="Pendiente"
        )

        # Crear detalle de venta.
        DetalleVenta.objects.create(
            detalle_venta=venta,
            detalle_inscripcion=inscripcion,
            detalle_precio=precio,
            detalle_cantidad=1
        )

        return venta


# REGISTRAR EL RESULTADO DE WEBPAY



def registrar_resultado_webpay(pago_id, respuesta):
    """
    Concilia el resultado de Transbank.

    True: pago confirmado.
    False: pago rechazado o revertido.
    None: pendiente o incidencia que requiere revisión.

    No confirma dos pagos de una misma venta.
    No incrementa dos veces los cupos.
    """

    with transaction.atomic():

        # Bloquear primero la venta, de manera
        # consistente con iniciar_pago_webpay().
        venta_id = Pago.objects.get(
            pk=pago_id
        ).pago_venta_id

        venta = (
            Venta.objects
            .select_for_update()
            .get(pk=venta_id)
        )

        pago = (
            Pago.objects
            .select_for_update()
            .get(pk=pago_id)
        )

        detalle = (
            DetalleVenta.objects
            .select_related(
                "detalle_inscripcion__inscripcion_torneo"
            )
            .get(detalle_venta=venta)
        )

        inscripcion = detalle.detalle_inscripcion

        # Validar identidad y monto.
        if (
            respuesta.get("buy_order")
            != pago.pago_orden_compra
            or respuesta.get("amount")
            != pago.pago_monto
        ):
            raise ValidationError(
                "La orden o el monto de Webpay no coincide."
            )

        if venta.venta_total != pago.pago_monto:
            raise ValidationError(
                "El monto no coincide con la venta."
            )

        estado_transbank = respuesta.get(
            "status", ""
        )

        pago.pago_estado_transbank = estado_transbank
        pago.pago_ultima_verificacion = timezone.now()

        campos_basicos = [
            "pago_estado",
            "pago_estado_transbank",
            "pago_ultima_verificacion",
        ]

        # Un pago aprobado no vuelve a procesarse.
        if pago.pago_estado == "Aprobado":
            pago.save(
                update_fields=[
                    "pago_estado_transbank",
                    "pago_ultima_verificacion",
                ]
            )
            return True

        # Una incidencia ya identificada necesita
        # resolución controlada, no automática.
        if pago.pago_estado == "Incidencia":
            pago.save(
                update_fields=[
                    "pago_estado_transbank",
                    "pago_ultima_verificacion",
                ]
            )
            return None

        # INITIALIZED no equivale a un rechazo.
        if estado_transbank == "INITIALIZED":

            if pago.pago_estado == "Pendiente":
                pago.pago_estado = "Revision"

            pago.save(update_fields=campos_basicos)
            return None

        # Resultados negativos conocidos.
        if estado_transbank in (
            "FAILED",
            "REVERSED",
            "NULLIFIED",
        ):
            pago.pago_estado = "Rechazado"
            pago.save(update_fields=campos_basicos)
            return False

        # Cualquier resultado no confirmado
        # que no sea de los anteriores debe
        # examinarse antes de permitir más cobros.
        if (
            estado_transbank != "AUTHORIZED"
            or respuesta.get("response_code") != 0
        ):
            pago.pago_estado = "Incidencia"
            pago.save(update_fields=campos_basicos)
            return None

        # El pago está autorizado en Transbank.
        # Comprobar si otra transacción ya pagó
        # esta venta.
        existe_otro_aprobado = (
            Pago.objects.filter(
                pago_venta=venta,
                pago_estado="Aprobado",
            )
            .exclude(pk=pago.pk)
            .exists()
        )

        if (
            existe_otro_aprobado
            or venta.venta_estado != "Pendiente"
            or inscripcion.inscripcion_estado != "Pendiente"
        ):
            pago.pago_estado = "Incidencia"
            pago.save(update_fields=campos_basicos)
            return None

        # Si existe otro intento activo,
        # no completar automáticamente este
        # pago antiguo.
        existe_otro_abierto = (
            Pago.objects.filter(
                pago_venta=venta,
                pago_estado__in=[
                    "Pendiente",
                    "Revision",
                ],
            )
            .exclude(pk=pago.pk)
            .exists()
        )

        if existe_otro_abierto:
            pago.pago_estado = "Incidencia"
            pago.save(update_fields=campos_basicos)
            return None

        # Confirmar únicamente si el torneo
        # sigue publicado y tiene cupos.
        torneo = inscripcion.inscripcion_torneo

        actualizados = Torneo.objects.filter(
            pk=torneo.pk,
            torneo_estado="Publicado",
            torneo_cuposOcupados__lt=F(
                "torneo_cupoMaximo"
            ),
        ).update(
            torneo_cuposOcupados=F(
                "torneo_cuposOcupados"
            ) + 1
        )

        if actualizados != 1:
            pago.pago_estado = "Incidencia"
            pago.save(update_fields=campos_basicos)
            return None

        # Pago autorizado y cupo asignado.
        pago.pago_estado = "Aprobado"
        pago.pago_codigo_autorizacion = str(
            respuesta.get("authorization_code") or ""
        )

        pago.save(
            update_fields=campos_basicos + [
                "pago_codigo_autorizacion",
            ]
        )

        venta.venta_estado = "Pagada"
        venta.save(
            update_fields=["venta_estado"]
        )

        inscripcion.inscripcion_estado = "Confirmada"
        inscripcion.save(
            update_fields=["inscripcion_estado"]
        )

        return True


