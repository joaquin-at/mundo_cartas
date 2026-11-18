
from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from pagos.models import Pago, Venta


class Command(BaseCommand):

    help = (
        "Audita pagos Webpay y detecta "
        "inconsistencias sin modificar datos."
    )

    def handle(self, *args, **options):

        problemas = []

        # 1. Transbank registra autorización,
        # pero Mundo Cartas no tiene el pago aprobado.
        pagos_por_revisar = Pago.objects.filter(
            pago_estado_transbank__in=[
                "AUTHORIZED",
                "CAPTURED",
                "PARTIALLY_NULLIFIED",
            ]
        ).exclude(
            pago_estado="Aprobado"
        )

        for pago in pagos_por_revisar:
            problemas.append(
                f"Pago #{pago.id}: Transbank informa "
                f"{pago.pago_estado_transbank}, "
                f"pero su estado local es "
                f"{pago.pago_estado}. "
                f"Venta #{pago.pago_venta_id}."
            )

        # 2. Más de un pago aprobado
        # para una misma venta.
        ventas_duplicadas = (
            Venta.objects
            .annotate(
                aprobados=Count(
                    "pagos",
                    filter=Q(
                        pagos__pago_estado="Aprobado"
                    ),
                )
            )
            .filter(aprobados__gt=1)
        )

        for venta in ventas_duplicadas:
            problemas.append(
                f"Venta #{venta.id}: tiene "
                f"{venta.aprobados} pagos aprobados."
            )

        # 3. Venta pagada sin un pago aprobado.
        ventas_sin_pago = (
            Venta.objects
            .filter(venta_estado="Pagada")
            .annotate(
                aprobados=Count(
                    "pagos",
                    filter=Q(
                        pagos__pago_estado="Aprobado"
                    ),
                )
            )
            .filter(aprobados=0)
        )

        for venta in ventas_sin_pago:
            problemas.append(
                f"Venta #{venta.id}: aparece Pagada "
                f"pero no tiene pagos aprobados."
            )

        # 4. Pago aprobado con venta no pagada.
        pagos_inconsistentes = (
            Pago.objects
            .filter(pago_estado="Aprobado")
            .exclude(
                pago_venta__venta_estado="Pagada"
            )
        )

        for pago in pagos_inconsistentes:
            problemas.append(
                f"Pago #{pago.id}: está Aprobado, "
                f"pero su venta no está Pagada."
            )

        # 5. Venta pagada con inscripción
        # que todavía no figura Confirmada.
        inscripciones_inconsistentes = (
            Venta.objects
            .filter(venta_estado="Pagada")
            .exclude(
                detalle__detalle_inscripcion__inscripcion_estado=(
                    "Confirmada"
                )
            )
        )

        for venta in inscripciones_inconsistentes:
            problemas.append(
                f"Venta #{venta.id}: está Pagada, "
                f"pero su inscripción no está Confirmada."
            )

        # 6. Intento marcado Expirado
        # pese a haberse iniciado commit().
        expirados_con_commit = Pago.objects.filter(
            pago_estado="Expirado",
            pago_commit_iniciado_en__isnull=False,
        )

        for pago in expirados_con_commit:
            problemas.append(
                f"Pago #{pago.id}: está Expirado "
                f"pero tiene un commit iniciado."
            )

        
        # 7. Detectar pagos que requieren
        # resolución de una incidencia.
        pagos_con_incidencia = (
            Pago.objects
            .filter(pago_estado="Incidencia")
            .select_related("pago_venta")
        )

        for pago in pagos_con_incidencia:
            problemas.append(
                f"Pago #{pago.id}: tiene una incidencia "
                f"pendiente de resolución. "
                f"Estado Transbank: "
                f"{pago.pago_estado_transbank or 'Desconocido'}. "
                f"Venta #{pago.pago_venta_id}. "
                f"Verificar posible cobro y devolución."
            )


        # Mostrar resultados.
        self.stdout.write(
            "Auditoría de pagos Webpay - Mundo Cartas"
        )

        if not problemas:
            self.stdout.write(
                self.style.SUCCESS(
                    "No se encontraron inconsistencias "
                    "en los registros revisados."
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"Se encontraron {len(problemas)} "
                f"situaciones para revisar:"
            )
        )

        for problema in problemas:
            self.stdout.write(
                self.style.ERROR(
                    f"- {problema}"
                )
            )

        self.stdout.write(
            self.style.WARNING(
                "No se modificó ningún pago. "
                "Revisar antes de realizar devoluciones "
                "o permitir nuevos cobros."
            )
        )
