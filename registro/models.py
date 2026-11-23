from django.conf import settings
from django.db import models
from django.core.validators import FileExtensionValidator
from pathlib import Path
from uuid import uuid4


def ruta_foto_perfil(instance, filename):
    return f"perfiles/{uuid4().hex}{Path(filename).suffix.lower()}"


class Rol(models.Model):
    nombre = models.CharField(max_length=30, unique=True)
    class Meta:
        verbose_name_plural = "Roles"
    def __str__(self):
        return self.nombre
def rol_jugador_default():
    rol, _ = Rol.objects.get_or_create(nombre="Jugador")
    return rol.pk


class Perfil(models.Model):
    telefono = models.CharField(max_length=16, blank=True)
    desactivacion_solicitada_el = models.DateTimeField(null=True, blank=True)
    motivo_desactivacion = models.CharField(max_length=500, blank=True)

    foto = models.ImageField(
        upload_to=ruta_foto_perfil,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])],
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    rol = models.ForeignKey(
        Rol,
        on_delete=models.RESTRICT,
        default=rol_jugador_default,
    )
    class Meta:
        verbose_name_plural = "Perfiles"
    def __str__(self):
        return f"{self.user.username} - {self.rol.nombre}"
