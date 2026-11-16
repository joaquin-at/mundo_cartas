from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

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
    torneo_precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
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