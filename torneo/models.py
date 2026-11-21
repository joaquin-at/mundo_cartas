from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.conf import settings

# Create your models here.

class Juego(models.Model):
    juego_nombre = models.CharField(max_length=100, unique=True)
    juego_activo = models.BooleanField(default=True)
    juego_imagen = models.ImageField(upload_to="juegos/", blank=True)

    def __str__(self):
        return self.juego_nombre


class Liga(models.Model):
    liga_juego = models.ForeignKey(
        Juego,
        on_delete=models.PROTECT,
        related_name="ligas"
    )
    liga_nombre = models.CharField(max_length=150)
    liga_inicio = models.DateField()
    liga_fin = models.DateField()
    liga_estado = models.CharField(
        max_length=30,
        default="Activa"
    )

    def __str__(self):
        return self.liga_nombre


class Torneo(models.Model):
    ESTADOS = [
        ("Borrador", "Borrador"),
        ("Publicado", "Publicado"),
        ("Cancelado", "Cancelado"),
        ("Finalizado", "Finalizado"),
    ]

    torneo_nombre = models.CharField(max_length=150)
    torneo_inicio = models.DateTimeField()
    torneo_precio = models.PositiveIntegerField()
    torneo_cupoMaximo = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    torneo_cuposOcupados = models.PositiveIntegerField(default=0)
    torneo_estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="Borrador"
    )
    torneo_juego = models.ForeignKey(
        Juego,
        on_delete=models.PROTECT,
        related_name="torneos",
    )
    torneo_liga = models.ForeignKey(
        Liga,
        on_delete=models.PROTECT,
        related_name="torneos",
        null=True,
        blank=True
    )

    @property
    def cupos_disponibles(self):
        return max(
            self.torneo_cupoMaximo - self.torneo_cuposOcupados,
            0
        )

    def clean(self):
        super().clean()

        if self.torneo_liga_id and self.torneo_juego_id:
            if (
                self.torneo_liga.liga_juego_id
                != self.torneo_juego_id
            ):
                raise ValidationError(
                    "La liga debe pertenecer al mismo juego del torneo."
                )

        if (
            self.torneo_cuposOcupados is not None
            and self.torneo_cupoMaximo is not None
        ):
            if (
                self.torneo_cuposOcupados
                > self.torneo_cupoMaximo
            ):
                raise ValidationError({
                    "torneo_cupoMaximo":
                        "El cupo máximo no puede ser menor "
                        "que los cupos ocupados."
                })

    def __str__(self):
        return self.torneo_nombre


class Inscripcion(models.Model):
    ESTADOS = [
        ("Pendiente", "Pendiente"),
        ("Confirmada", "Confirmada"),
        ("Cancelada", "Cancelada"),
    ]

    inscripcion_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name = "inscripciones",
    )

    inscripcion_torneo = models.ForeignKey(
        Torneo,
        on_delete=models.RESTRICT,
        related_name="inscripciones",
    )

    inscripcion_estado = models.CharField(
        max_length=20,
        choices = ESTADOS,
        default = "Pendiente"
    )

    inscripcion_precio = models.PositiveIntegerField()

    inscripcion_fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields = [
                    "inscripcion_usuario",
                    "inscripcion_torneo",
                ],
                name = "unique_inscripcion_usuario_torneo",
            )
        ]
        def __str__(self):
            return (
                f"{self.inscripcion_usuario.username} - "
                f"{self.inscripcion_torneo.torneo_nombre}"
            )

class ResultadoTorneo(models.Model):
    inscripcion = models.OneToOneField(
        "torneo.Inscripcion",
        on_delete=models.PROTECT,
        related_name="resultado_torneo_nuevo",
    )

    participo = models.BooleanField(default=False)

    victorias = models.PositiveIntegerField(default=0)
    empates = models.PositiveIntegerField(default=0)
    derrotas = models.PositiveIntegerField(default=0)

    posicion_final = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    def calcular_puntos_torneo(self, regla):
        return (
            self.victorias * regla.puntos_victoria
            + self.empates * regla.puntos_empate
            + self.derrotas * regla.puntos_derrota
        )

    def __str__(self):
        return f"Resultado de {self.inscripcion}"
class ReglaPuntuacionTorneo(models.Model):
    nombre = models.CharField(
        max_length=100,
        unique=True,
    )

    puntos_victoria = models.PositiveIntegerField(default=3)
    puntos_empate = models.PositiveIntegerField(default=1)
    puntos_derrota = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.nombre
