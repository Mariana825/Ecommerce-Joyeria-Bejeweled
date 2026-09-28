"""
Cliente para la API REST de PayPal (Orders v2), en modo Sandbox por defecto.

Flujo que implementa (el estándar "Smart Buttons" de PayPal):
    1. El navegador pide crear la orden -> crear_orden(pedido)
    2. El comprador aprueba el pago en la ventana de PayPal
    3. El navegador pide capturar la orden -> capturar_orden(id_orden_paypal)

Documentación: https://developer.paypal.com/docs/api/orders/v2/
"""

import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

TIEMPO_ESPERA_SEGUNDOS = 10
CLAVE_CACHE_TOKEN = 'paypal:access_token'


class ErrorPayPal(Exception):
    """Se lanza cuando PayPal responde con un error o la petición falla."""


def _url(ruta):
    return f'{settings.PAYPAL_API_BASE}{ruta}'


def obtener_token_acceso():
    """
    Obtiene (o reutiliza desde caché) un token de acceso OAuth2 de PayPal.

    PayPal emite tokens con una vigencia de varias horas; los guardamos en
    caché un poco menos de lo que dura el token para no pedir uno en cada
    petición.
    """
    token = cache.get(CLAVE_CACHE_TOKEN)
    if token:
        return token

    try:
        respuesta = requests.post(
            _url('/v1/oauth2/token'),
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
            data={'grant_type': 'client_credentials'},
            headers={'Accept': 'application/json'},
            timeout=TIEMPO_ESPERA_SEGUNDOS,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
    except (requests.RequestException, ValueError) as error:
        raise ErrorPayPal(f'No se pudo autenticar con PayPal: {error}') from error

    token = datos['access_token']
    # Restamos un margen de 60 segundos por seguridad.
    vigencia = max(60, int(datos.get('expires_in', 3600)) - 60)
    cache.set(CLAVE_CACHE_TOKEN, token, vigencia)
    return token


def _peticion(metodo, ruta, cuerpo=None):
    token = obtener_token_acceso()
    try:
        respuesta = requests.request(
            metodo,
            _url(ruta),
            json=cuerpo,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            timeout=TIEMPO_ESPERA_SEGUNDOS,
        )
    except requests.RequestException as error:
        raise ErrorPayPal(f'No se pudo conectar con PayPal: {error}') from error

    if not respuesta.ok:
        logger.warning('PayPal respondió %s: %s', respuesta.status_code, respuesta.text)
        raise ErrorPayPal(f'PayPal respondió con un error ({respuesta.status_code}).')

    return respuesta.json() if respuesta.content else {}


def crear_orden(pedido):
    """
    Crea una orden de PayPal para el total del `pedido` y regresa su ID
    (el que el botón de PayPal en el navegador necesita para continuar).
    """
    cuerpo = {
        'intent': 'CAPTURE',
        'purchase_units': [
            {
                'reference_id': str(pedido.id),
                'description': f'Pedido #{pedido.id} — Bejeweled',
                'amount': {
                    'currency_code': settings.PAYPAL_CURRENCY,
                    'value': f'{pedido.total:.2f}',
                },
            }
        ],
        'application_context': {
            'brand_name': 'Bejeweled',
            'shipping_preference': 'NO_SHIPPING',
            'user_action': 'PAY_NOW',
        },
    }
    orden = _peticion('POST', '/v2/checkout/orders', cuerpo)
    return orden['id']


def capturar_orden(id_orden_paypal):
    """
    Confirma (captura) el pago de una orden ya aprobada por el comprador.
    Regresa el diccionario completo de la respuesta de PayPal.
    """
    return _peticion('POST', f'/v2/checkout/orders/{id_orden_paypal}/capture')


def obtener_id_captura(respuesta_captura):
    """Extrae el ID de la transacción capturada, para guardarlo como referencia."""
    try:
        return (
            respuesta_captura['purchase_units'][0]
            ['payments']['captures'][0]['id']
        )
    except (KeyError, IndexError):
        return respuesta_captura.get('id', '')
