
from datetime import date

from django.urls import reverse
from registro.models import Perfil, Rol

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import Juego, Liga, Torneo, Inscripcion, ResultadoTorneo, ReglaPuntuacionTorneo
from .services import obtener_clasificacion_liga,obtener_ranking_por_juego


class ClasificacionLigaTests(TestCase):

    def test_acumula_puntos_solo_de_torneos_de_la_liga(self):
        Usuario = get_user_model()

        jugador = Usuario.objects.create_user(
            username="jugador_prueba",
            password="clave_prueba_123",
        )

        juego = Juego.objects.create(
            juego_nombre="Pokémon de prueba"
        )

        liga = Liga.objects.create(
            liga_nombre="Liga de prueba",
            liga_juego=juego,
            liga_inicio=date(2026, 1, 1),
            liga_fin=date(2026, 12, 31),
        )

        casos = [
            ("Fecha 1", liga, "Finalizado", 1),
            ("Fecha 2", liga, "Finalizado", 2),
            ("Torneo independiente", None, "Finalizado", 1),
            ("Torneo cancelado", liga, "Cancelado", 1),
        ]

        for nombre, liga_torneo, estado, posicion in casos:
            torneo = Torneo.objects.create(
                torneo_nombre=nombre,
                torneo_inicio=timezone.now(),
                torneo_precio=5000,
                torneo_cupoMaximo=8,
                torneo_estado=estado,
                torneo_juego=juego,
                torneo_liga=liga_torneo,
            )

            inscripcion = Inscripcion.objects.create(
                inscripcion_usuario=jugador,
                inscripcion_torneo=torneo,
                inscripcion_estado="Confirmada",
                inscripcion_precio=5000,
            )

            ResultadoTorneo.objects.create(
                inscripcion=inscripcion,
                participo=True,
                posicion_final=posicion,
            )

        clasificacion = obtener_clasificacion_liga(liga)

        self.assertEqual(len(clasificacion), 1)
        self.assertEqual(clasificacion[0]["jugador"], jugador)
        self.assertEqual(clasificacion[0]["puntos"], 9)
        self.assertEqual(clasificacion[0]["torneos_jugados"], 2)

class PuntosHistoricosTests(TestCase):

    def test_editar_resultado_conserva_regla_original(self):
        Usuario = get_user_model()

        administrador = Usuario.objects.create_user(
            username="admin_prueba_puntos",
            password="clave_prueba_123",
        )

        rol, _ = Rol.objects.get_or_create(
            nombre="Administrador"
        )

        Perfil.objects.update_or_create(
            user=administrador,
            defaults={"rol": rol},
        )

        self.client.force_login(administrador)

        jugador = Usuario.objects.create_user(
            username="jugador_puntos",
            password="clave_prueba_123",
        )

        juego = Juego.objects.create(
            juego_nombre="Juego para probar puntos"
        )

        torneo = Torneo.objects.create(
            torneo_nombre="Torneo de puntos históricos",
            torneo_inicio=timezone.now(),
            torneo_precio=5000,
            torneo_cupoMaximo=8,
            torneo_estado="Finalizado",
            torneo_juego=juego,
        )

        inscripcion = Inscripcion.objects.create(
            inscripcion_usuario=jugador,
            inscripcion_torneo=torneo,
            inscripcion_estado="Confirmada",
            inscripcion_precio=5000,
        )

        regla, _ = ReglaPuntuacionTorneo.objects.get_or_create(
            nombre="Puntuación estándar",
        )

        regla.puntos_victoria = 3
        regla.puntos_empate = 1
        regla.puntos_derrota = 0
        regla.save()

        url = reverse(
            "admin_registrar_resultado",
            kwargs={
                "pk": torneo.pk,
                "inscripcion_id": inscripcion.pk,
            },
        )

        datos = {
            "participo": "on",
            "victorias": "2",
            "empates": "0",
            "derrotas": "0",
            "posicion_final": "1",
        }

        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 302)

        resultado = ResultadoTorneo.objects.get(
            inscripcion=inscripcion
        )

        self.assertEqual(resultado.puntos_torneo_guardados, 6)
        self.assertEqual(resultado.puntos_victoria_aplicados, 3)

        # Cambiamos la regla para resultados futuros.
        regla.puntos_victoria = 4
        regla.save()

        # Corregimos el resultado antiguo a 3 victorias.
        datos["victorias"] = "3"

        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 302)

        resultado.refresh_from_db()

        # Debe usar la regla original: 3 victorias × 3.
        self.assertEqual(resultado.puntos_torneo_guardados, 9)
        self.assertEqual(resultado.puntos_victoria_aplicados, 3)
class ConfiguracionPuntuacionTests(TestCase):

    def test_administrador_puede_configurar_puntos(self):
        Usuario = get_user_model()

        administrador = Usuario.objects.create_user(
            username="admin_configuracion",
            password="clave_prueba_123",
        )

        rol, _ = Rol.objects.get_or_create(
            nombre="Administrador"
        )

        Perfil.objects.update_or_create(
            user=administrador,
            defaults={"rol": rol},
        )

        self.client.force_login(administrador)

        regla, _ = ReglaPuntuacionTorneo.objects.get_or_create(
            nombre="Puntuación estándar",
        )

        respuesta = self.client.post(
            reverse("admin_configurar_puntuacion"),
            {
                "puntos_victoria": "4",
                "puntos_empate": "2",
                "puntos_derrota": "0",
            },
        )

        self.assertEqual(respuesta.status_code, 302)

        regla.refresh_from_db()

        self.assertEqual(regla.puntos_victoria, 4)
        self.assertEqual(regla.puntos_empate, 2)
        self.assertEqual(regla.puntos_derrota, 0)
class RankingPorJuegoTests(TestCase):

    def test_ranking_separa_los_juegos(self):
        Usuario = get_user_model()

        jugador1 = Usuario.objects.create_user(
            username="jugador_ranking_1",
            password="clave_prueba_123",
        )

        jugador2 = Usuario.objects.create_user(
            username="jugador_ranking_2",
            password="clave_prueba_123",
        )

        juego1 = Juego.objects.create(
            juego_nombre="Juego A"
        )

        juego2 = Juego.objects.create(
            juego_nombre="Juego B"
        )

        casos = [
            (jugador1, juego1, 6),
            (jugador2, juego1, 4),
            (jugador2, juego2, 2),
        ]

        for numero, (jugador, juego, puntos) in enumerate(casos):
            torneo = Torneo.objects.create(
                torneo_nombre=f"Torneo ranking {numero}",
                torneo_inicio=timezone.now(),
                torneo_precio=0,
                torneo_cupoMaximo=8,
                torneo_estado="Finalizado",
                torneo_juego=juego,
            )

            inscripcion = Inscripcion.objects.create(
                inscripcion_usuario=jugador,
                inscripcion_torneo=torneo,
                inscripcion_estado="Confirmada",
                inscripcion_precio=0,
            )

            ResultadoTorneo.objects.create(
                inscripcion=inscripcion,
                participo=True,
                posicion_final=1,
                puntos_torneo_guardados=puntos,
            )

        ranking = obtener_ranking_por_juego()

        posiciones = [
            (
                fila["juego"],
                fila["jugador"],
                fila["puntos"],
                fila["posicion"],
            )
            for fila in ranking
        ]

        self.assertEqual(posiciones, [
            ("Juego A", "jugador_ranking_1", 6, 1),
            ("Juego A", "jugador_ranking_2", 4, 2),
            ("Juego B", "jugador_ranking_2", 2, 1),
        ])
