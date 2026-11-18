
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from django.urls import reverse

from torneo.models import Torneo, Inscripcion, Juego
from pagos.models import Pago, Venta, DetalleVenta
from pagos.services import registrar_resultado_webpay
from pagos.conciliacion import revisar_pagos_pendientes


class SeguridadWebpayTests(TestCase):

    def setUp(self):
        """
        Crear datos de prueba independientes.

        Django utiliza una base de datos de pruebas,
        no los pagos de tu proyecto local.
        """

        self.usuario = get_user_model().objects.create_user(
            username="jugador_seguridad",
            password="ClaveDePrueba123!",
        )

        self.juego = Juego.objects.create(
            juego_nombre="Juego de prueba",
            juego_activo=True,
        )

        self.torneo = Torneo.objects.create(
            torneo_juego=self.juego,
            torneo_nombre="Torneo de seguridad",
            torneo_inicio=timezone.now()
            + timedelta(days=5),
            torneo_precio=Decimal("2500.00"),
            torneo_cupoMaximo=1,
            torneo_cuposOcupados=0,
            torneo_estado="Publicado",
        )

        self.inscripcion = Inscripcion.objects.create(
            inscripcion_usuario=self.usuario,
            inscripcion_torneo=self.torneo,
            inscripcion_estado="Pendiente",
            inscripcion_precio=2500,
        )

        self.venta = Venta.objects.create(
            venta_usuario=self.usuario,
            venta_total=2500,
            venta_estado="Pendiente",
        )

        DetalleVenta.objects.create(
            detalle_venta=self.venta,
            detalle_inscripcion=self.inscripcion,
            detalle_precio=2500,
            detalle_cantidad=1,
        )


    def test_no_inicia_pago_si_torneo_esta_lleno(self):

        # Simular que se ocupó el último cupo.
        self.torneo.torneo_cuposOcupados = (
            self.torneo.torneo_cupoMaximo
        )
        self.torneo.save(
            update_fields=["torneo_cuposOcupados"]
        )

        # Iniciar sesión con el jugador de prueba.
        self.client.force_login(self.usuario)

        # Evitar conexiones reales a Transbank.
        with patch(
            "pagos.views.crear_transaccion_webpay"
        ) as crear_transaccion:

            respuesta = self.client.post(
                reverse(
                    "iniciar_pago_webpay",
                    args=[self.inscripcion.id],
                )
            )

        # Debe regresar al resumen de pago.
        self.assertEqual(
            respuesta.status_code,
            302,
        )

        self.assertEqual(
            respuesta.url,
            reverse(
                "resumen_pago",
                args=[self.inscripcion.id],
            ),
        )

        # No se debe llamar a Transbank.
        crear_transaccion.assert_not_called()

        # No se debe crear ningún intento nuevo.
        self.assertEqual(
            Pago.objects.filter(
                pago_venta=self.venta,
            ).count(),
            0,
        )

    
    def test_incidencia_entra_en_conciliacion(self):

        pago = self.crear_pago(
            "PRUEBA-INCIDENCIA",
            "Incidencia",
        )

        pago.pago_revisar_desde = (
            timezone.now() - timedelta(minutes=1)
        )

        pago.save(
            update_fields=["pago_revisar_desde"]
        )

        # Simulamos la consulta para no conectar
        # realmente con Transbank.
        with patch(
            "pagos.conciliacion.consultar_pago_webpay"
        ) as consulta:

            consulta.return_value = {
                "resultado": "AUTHORIZED",
                "pago_id": pago.id,
                "estado_local": "Incidencia",
            }

            resultados = revisar_pagos_pendientes()

        consulta.assert_called_once_with(pago.id)

        self.assertEqual(len(resultados), 1)
        self.assertEqual(
            resultados[0]["estado_local"],
            "Incidencia",
        )


    def crear_pago(self, orden, estado="Pendiente"):
        return Pago.objects.create(
            pago_venta=self.venta,
            pago_monto=2500,
            pago_estado=estado,
            pago_metodo="Webpay",
            pago_orden_compra=orden,
            pago_token=f"TOKEN-{orden}",
        )

    def respuesta_autorizada(self, pago):
        """
        Respuesta simulada de Transbank.
        No realiza ninguna conexión externa.
        """
        return {
            "buy_order": pago.pago_orden_compra,
            "amount": 2500,
            "status": "AUTHORIZED",
            "response_code": 0,
            "authorization_code": "123456",
        }

    def test_pago_aprobado_confirma_inscripcion(self):
        pago = self.crear_pago("PRUEBA-1")

        resultado = registrar_resultado_webpay(
            pago.id,
            self.respuesta_autorizada(pago),
        )

        pago.refresh_from_db()
        self.venta.refresh_from_db()
        self.inscripcion.refresh_from_db()
        self.torneo.refresh_from_db()

        self.assertTrue(resultado)
        self.assertEqual(pago.pago_estado, "Aprobado")
        self.assertEqual(self.venta.venta_estado, "Pagada")
        self.assertEqual(
            self.inscripcion.inscripcion_estado,
            "Confirmada",
        )
        self.assertEqual(
            self.torneo.torneo_cuposOcupados,
            1,
        )

    def test_pago_aprobado_dos_veces_no_duplica_cupos(self):
        pago = self.crear_pago("PRUEBA-2")
        respuesta = self.respuesta_autorizada(pago)

        resultado_1 = registrar_resultado_webpay(
            pago.id,
            respuesta,
        )

        resultado_2 = registrar_resultado_webpay(
            pago.id,
            respuesta,
        )

        self.torneo.refresh_from_db()

        self.assertTrue(resultado_1)
        self.assertTrue(resultado_2)
        self.assertEqual(
            self.torneo.torneo_cuposOcupados,
            1,
        )

    def test_pago_initialized_no_es_rechazado(self):
        pago = self.crear_pago("PRUEBA-3")

        respuesta = {
            "buy_order": pago.pago_orden_compra,
            "amount": 2500,
            "status": "INITIALIZED",
        }

        resultado = registrar_resultado_webpay(
            pago.id,
            respuesta,
        )

        pago.refresh_from_db()
        self.inscripcion.refresh_from_db()

        self.assertIsNone(resultado)
        self.assertEqual(pago.pago_estado, "Revision")
        self.assertEqual(
            self.inscripcion.inscripcion_estado,
            "Pendiente",
        )

    def test_sin_cupos_genera_incidencia(self):
        # Simular que el torneo ya está lleno.
        self.torneo.torneo_cuposOcupados = 1
        self.torneo.save(
            update_fields=["torneo_cuposOcupados"]
        )

        pago = self.crear_pago("PRUEBA-4")

        resultado = registrar_resultado_webpay(
            pago.id,
            self.respuesta_autorizada(pago),
        )

        pago.refresh_from_db()
        self.venta.refresh_from_db()
        self.inscripcion.refresh_from_db()
        self.torneo.refresh_from_db()

        self.assertIsNone(resultado)
        self.assertEqual(
            pago.pago_estado,
            "Incidencia",
        )
        self.assertEqual(
            self.venta.venta_estado,
            "Pendiente",
        )
        self.assertEqual(
            self.inscripcion.inscripcion_estado,
            "Pendiente",
        )
        self.assertEqual(
            self.torneo.torneo_cuposOcupados,
            1,
        )

    def test_autorizacion_tardia_no_duplica_venta(self):
        # Intento antiguo que expiró localmente.
        antiguo = self.crear_pago(
            "PRUEBA-ANTIGUA",
            "Expirado",
        )

        # El jugador realiza otro intento.
        nuevo = self.crear_pago(
            "PRUEBA-NUEVA",
        )

        resultado_nuevo = registrar_resultado_webpay(
            nuevo.id,
            self.respuesta_autorizada(nuevo),
        )

        # Transbank informa después que el
        # intento antiguo también fue autorizado.
        resultado_antiguo = registrar_resultado_webpay(
            antiguo.id,
            self.respuesta_autorizada(antiguo),
        )

        antiguo.refresh_from_db()
        nuevo.refresh_from_db()
        self.torneo.refresh_from_db()

        self.assertTrue(resultado_nuevo)
        self.assertIsNone(resultado_antiguo)

        self.assertEqual(
            antiguo.pago_estado,
            "Incidencia",
        )
        self.assertEqual(
            nuevo.pago_estado,
            "Aprobado",
        )
        self.assertEqual(
            self.torneo.torneo_cuposOcupados,
            1,
        )

        self.assertEqual(
            Pago.objects.filter(
                pago_venta=self.venta,
                pago_estado="Aprobado",
            ).count(),
            1,
        )

    def test_no_permite_dos_pagos_abiertos(self):
        self.crear_pago(
            "PRUEBA-PENDIENTE",
            "Pendiente",
        )

        # La restricción de base de datos debe
        # impedir un segundo intento abierto.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.crear_pago(
                    "PRUEBA-REVISION",
                    "Revision",
                )

        self.assertEqual(
            Pago.objects.filter(
                pago_venta=self.venta,
                pago_estado__in=[
                    "Pendiente",
                    "Revision",
                ],
            ).count(),
            1,
        )
