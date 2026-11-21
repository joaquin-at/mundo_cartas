from django.db import models

# Create your models here.
class ResultadoTorneo(models.Model):
    inscripcion = models.OneToOneField(
        "torneo.Inscripcion",
        on_delete=models.PROTECT,
        related_name="resultado",
    )

    participo = models.BooleanField(default=False)

    victorias = models.PositiveIntegerField(default=0)
    empates = models.PositiveIntegerField(default=0)
    derrotas = models.PositiveIntegerField(default=0)

    posicion_final = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Resultado de {self.inscripcion}"

    def calcular_puntos_torneo(self, regla):
        return (
            self.victorias * regla.puntos_victoria
            + self.empates * regla.puntos_empate
            + self.derrotas * regla.puntos_derrota
        )

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