from .models import ResultadoTorneo


def obtener_clasificacion_liga(liga):
    if liga is None or liga.pk is None:
        return []

    resultados = (
        ResultadoTorneo.objects
        .filter(
            inscripcion__inscripcion_torneo__torneo_liga=liga,
            inscripcion__inscripcion_torneo__torneo_estado="Finalizado",
            inscripcion__inscripcion_estado="Confirmada",
            participo=True,
            posicion_final__isnull=False,
        )
        .select_related("inscripcion__inscripcion_usuario")
    )

    clasificacion = {}

    for resultado in resultados:
        jugador = resultado.inscripcion.inscripcion_usuario

        if jugador.pk not in clasificacion:
            clasificacion[jugador.pk] = {
                "jugador": jugador,
                "puntos": 0,
                "torneos_jugados": 0,
            }

        clasificacion[jugador.pk]["puntos"] += resultado.calcular_puntos_liga()
        clasificacion[jugador.pk]["torneos_jugados"] += 1

    return sorted(
        clasificacion.values(),
        key=lambda fila: (
            -fila["puntos"],
            fila["jugador"].username.lower(),
        ),
    )
