
from transbank.webpay.webpay_plus.transaction import Transaction

from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType
from transbank.common.integration_commerce_codes import (
    IntegrationCommerceCodes,
)
from transbank.common.integration_api_keys import (
    IntegrationApiKeys,
)


def obtener_cliente_webpay():
    """
    Configura Webpay Plus en ambiente de pruebas.
    No realiza ningún cobro.
    """

    opciones = WebpayOptions(
        IntegrationCommerceCodes.WEBPAY_PLUS,
        IntegrationApiKeys.WEBPAY,
        IntegrationType.TEST,
    )

    return Transaction(opciones)


def crear_transaccion_webpay(
    orden_compra,
    sesion_id,
    monto,
    url_retorno,
):
    """
    Solicita a Transbank una transacción.

    Devuelve un diccionario con:
    - token: identificador de la transacción
    - url: dirección del formulario de Webpay
    """

    if not isinstance(monto, int) or monto <= 0:
        raise ValueError(
            "El monto debe ser un entero positivo en pesos chilenos."
        )

    cliente = obtener_cliente_webpay()

    respuesta = cliente.create(
        orden_compra,
        sesion_id,
        monto,
        url_retorno,
    )

    return respuesta


def confirmar_transaccion_webpay(token):
    """
    Confirma la transacción con Transbank
    y obtiene su resultado real.

    Esta función NO modifica todavía la base de datos.
    """

    if not token:
        raise ValueError(
            "Se necesita un token para confirmar el pago."
        )

    cliente = obtener_cliente_webpay()

    respuesta = cliente.commit(token)

    return respuesta
