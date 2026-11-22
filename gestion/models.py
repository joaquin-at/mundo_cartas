from django.conf import settings
from django.db import models


# Create your models here.

class ComentarioSugerencia(models.Model):

    TIPOS = [
        ("comentario", "Comentario"),
        ("sugerencia", "Sugerencia"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="comentarios_sugerencias",
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
    )

    mensaje = models.TextField(
        max_length=500,
    )

    fecha_envio = models.DateTimeField(
        auto_now_add=True,
    )

    revisado = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["-fecha_envio"]

    def __str__(self):
        return (
            f"{self.get_tipo_display()} "
            f"de {self.usuario.username}"
        )
