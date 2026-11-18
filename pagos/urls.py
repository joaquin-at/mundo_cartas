
from django.urls import path

from . import views


urlpatterns = [
    path("resumen/<int:inscripcion_id>/", views.resumen_pago, name="resumen_pago",),
    path("iniciar/<int:inscripcion_id>/", views.iniciar_pago_webpay, name="iniciar_pago_webpay",),
    path("retorno/", views.retorno_webpay, name="retorno_webpay",),
]
