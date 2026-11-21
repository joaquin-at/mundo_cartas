
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import Juego, Liga, Torneo, Inscripcion, ResultadoTorneo
from .services import obtener_clasificacion_liga


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