from django.conf import settings
from django.db import models


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