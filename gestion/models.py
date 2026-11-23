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

    archivado = models.BooleanField(default=False, db_index=True)

    respuesta = models.TextField(max_length=1000, blank=True, default="")
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    respondido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="respuestas_comentarios",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-fecha_envio"]

    def __str__(self):
        return f"Comentario de {self.usuario.username}"
