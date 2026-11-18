
from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from pagos.conciliacion import (
    consultar_pago_webpay,
    revisar_pagos_pendientes,
)

from pagos.models import Pago


class Command(BaseCommand):

    help = (
        "Consulta y concilia los pagos de Webpay "
        "que necesitan revisión."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--pago",
            type=int,
            default=None,
            help=(
                "Consultar un pago específico por ID. "
                "Útil para pruebas y diagnóstico."
            ),
        )

    def handle(self, *args, **options):

        pago_id = options["pago"]

        self.stdout.write(
            "Iniciando conciliación de Webpay..."
        )

        if pago_id is not None:

            if not Pago.objects.filter(
                pk=pago_id
            ).exists():
                raise CommandError(
                    f"No existe el pago #{pago_id}."
                )

            resultados = [
                consultar_pago_webpay(pago_id)
            ]

        else:
            resultados = revisar_pagos_pendientes()

        if not resultados:
            self.stdout.write(
                "No hay pagos que requieran "
                "verificación en este momento."
            )
            return

        total = len(resultados)

        self.stdout.write(
            f"Intentos consultados: {total}"
        )

        for resultado in resultados:

            identificador = resultado.get(
                "pago_id",
                "Sin ID",
            )

            estado_transbank = resultado.get(
                "resultado",
                "Desconocido",
            )

            estado_local = resultado.get(
                "estado_local",
                "Desconocido",
            )

            mensaje = resultado.get(
                "mensaje",
                "",
            )

            self.stdout.write(
                f"\nPago #{identificador}"
            )

            self.stdout.write(
                f"  Transbank: {estado_transbank}"
            )

            self.stdout.write(
                f"  Mundo Cartas: {estado_local}"
            )

            self.stdout.write(
                f"  Resultado: {mensaje}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\nConciliación finalizada."
            )
        )
