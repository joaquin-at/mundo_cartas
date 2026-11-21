from .models import ResultadoTorneo
from django.db.models import Sum


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


def obtener_ranking_por_juego():
    
    totales = (
        ResultadoTorneo.objects
        .filter(
            inscripcion__inscripcion_estado="Confirmada",
            inscripcion__inscripcion_torneo__torneo_estado="Finalizado",
            participo=True,
            puntos_torneo_guardados__isnull=False,
        )
        .values(
            "inscripcion__inscripcion_torneo__torneo_juego_id",
            "inscripcion__inscripcion_torneo__torneo_juego__juego_nombre",
            "inscripcion__inscripcion_usuario_id",
            "inscripcion__inscripcion_usuario__username",
        )
        .annotate(
            puntos=Sum("puntos_torneo_guardados")
        )
        .order_by(
            "inscripcion__inscripcion_torneo__torneo_juego_id",
            "-puntos",
            "inscripcion__inscripcion_usuario__username",
        )
    )

    ranking = []
    juego_anterior = None
    puntos_anteriores = None
    numero_jugador = 0
    posicion = 0

    for fila in totales:
        juego_id = fila[
            "inscripcion__inscripcion_torneo__torneo_juego_id"
        ]

       
        if juego_id != juego_anterior:
            juego_anterior = juego_id
            puntos_anteriores = None
            numero_jugador = 0

        numero_jugador += 1

       
        if puntos_anteriores != fila["puntos"]:
            posicion = numero_jugador

        puntos_anteriores = fila["puntos"]

        ranking.append({
            "juego_id": juego_id,
            "juego": fila[
                "inscripcion__inscripcion_torneo__torneo_juego__juego_nombre"
            ],
            "jugador_id": fila["inscripcion__inscripcion_usuario_id"],
            "jugador": fila["inscripcion__inscripcion_usuario__username"],
            "puntos": fila["puntos"],
            "posicion": posicion,
        })

    return ranking