from django.contrib import admin

from .models import Venta, DetalleVenta, Pago

# Register your models here.

# ADMINISTRACIÓN DE VENTAS
@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "venta_usuario",
        "venta_fecha",
        "venta_total",
        "venta_estado",
    )

    list_filter = (
        "venta_estado",
        "venta_fecha",
    )

    search_fields = (
        "venta_usuario__username",
    )

    readonly_fields = (
        "venta_fecha",
        "venta_estado",
        "venta_total",
    )


# ADMINISTRACIÓN DE DETALLES DE VENTA
@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "detalle_venta",
        "detalle_inscripcion",
        "detalle_precio",
        "detalle_cantidad",
    )

    search_fields = (
        "detalle_venta__venta_usuario__username",
        "detalle_inscripcion__inscripcion_torneo__torneo_nombre",
    )

    readonly_fields = (
        "detalle_venta",
        "detalle_inscripcion",
        "detalle_precio",
        "detalle_cantidad",
    )


# ADMINISTRACIÓN DE PAGOS
@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pago_venta",
        "pago_fecha",
        "pago_monto",
        "pago_estado",
        "pago_metodo",
        "pago_orden_compra",
    )

    list_filter = (
        "pago_estado",
        "pago_metodo",
        "pago_fecha",
    )

    search_fields = (
        "pago_orden_compra",
        "pago_venta__venta_usuario__username",
    )

    readonly_fields = (
        "pago_venta",
        "pago_fecha",
        "pago_monto",
        "pago_estado",
        "pago_metodo",
        "pago_orden_compra",
        "pago_token",
        "pago_codigo_autorizacion",
    )

