from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Q

from torneo.models import Inscripcion
# Create your models here.

class Venta(models.Model):
    ESTADOS = [
        ("Pendiente", "Pendiente"),
        ("Pagada", "Pagada"),
        ("Cancelada", "Cancelada"),
    ]

    venta_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ventas"
    )

    venta_fecha = models.DateTimeField(
        auto_now_add=True
    )

    venta_total = models.PositiveIntegerField()

    venta_estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="Pendiente"
    )

    def __str__(self):
        return f"Venta #{self.pk} - {self.venta_usuario.username}"


# DETALLE DE LA VENTA
class DetalleVenta(models.Model):
    detalle_venta = models.OneToOneField(
        Venta,
        on_delete=models.PROTECT,
        related_name="detalle"
    )

    detalle_inscripcion = models.OneToOneField(
        Inscripcion,
        on_delete=models.PROTECT,
        related_name="detalle_venta"
    )

    detalle_precio = models.PositiveIntegerField()

    detalle_cantidad = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    def __str__(self):
        return f"Detalle de venta #{self.detalle_venta_id}"


# REGISTRO DE INTENTOS DE PAGO
class Pago(models.Model):
    ESTADOS = [
        ("Pendiente", "Pendiente"),
        ("Aprobado", "Aprobado"),
        ("Rechazado", "Rechazado"),
        ("Anulado", "Anulado"),
        ("Expirado", "Expirado"),
        ("Revision", "Revisión"),
        ("Incidencia", "Incidencia de pago"),
    ]

    pago_venta = models.ForeignKey(
        Venta,
        on_delete=models.PROTECT,
        related_name="pagos",
    )

    pago_fecha = models.DateTimeField(
        auto_now_add=True
    )

    pago_monto = models.PositiveIntegerField()

    pago_estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="Pendiente"
    )

    pago_metodo = models.CharField(
        max_length=30,
        default="Webpay"
    )

    pago_orden_compra = models.CharField(
        max_length=100,
        unique=True
    )

    pago_token = models.CharField(
        max_length=255,
        blank=True
    )

    pago_codigo_autorizacion = models.CharField(
        max_length=100,
        blank=True
    )

    pago_ultima_verificacion = models.DateTimeField(
        null=True,
        blank=True,
    )

    pago_estado_transbank = models.CharField(
        max_length=30,
        blank=True,
    )

    pago_revisar_desde = models.DateTimeField(
        null=True,
        blank=True,
    )

    pago_commit_iniciado_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["pago_venta"],
                condition=Q(
                    pago_estado__in=[
                        "Pendiente",
                        "Revision",
                    ]
                ),
                name="unique_pago_abierto_por_venta",
            ),
        ]

    def __str__(self):
        return f"Pago #{self.pk} - {self.pago_estado}"
