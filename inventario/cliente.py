"""
Cliente de la API de inventario.

Este módulo es la única puerta que el resto de la tienda (el checkout, por
ejemplo) usa para tocar el stock. En vez de restar `producto.existencias`
directamente en la base de datos, el checkout llama a estas funciones, que
hacen una petición HTTP real a `/api/inventario/...` — la misma API que
podría consumir otro sistema (una app móvil, un ERP, etc.).

El proyecto corre en HTTPS con un certificado autofirmado en desarrollo
(ver runsslserver en el README), así que por defecto no se verifica la
cadena de certificado (`verify=False`) para no bloquear las pruebas locales.
En producción, con un certificado real firmado por una autoridad
reconocida, debe usarse verify=True (ver INVENTARIO_VERIFICAR_SSL).
"""

import logging

import requests
import urllib3
from django.conf import settings

from .permissions import ENCABEZADO_API_KEY

logger = logging.getLogger(__name__)

TIEMPO_ESPERA_SEGUNDOS = 5

if not settings.INVENTARIO_VERIFICAR_SSL:
    # Evita que la consola se llene de InsecureRequestWarning por el
    # certificado autofirmado de desarrollo.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ErrorInventario(Exception):
    """Se lanza cuando la API de inventario no puede completar el ajuste."""


class StockInsuficiente(ErrorInventario):
    """Se lanza cuando la API respondió 409: ya no hay existencias suficientes."""


def _cabeceras():
    return {ENCABEZADO_API_KEY: settings.INVENTARIO_API_KEY}


def _url(ruta):
    return f'{settings.API_BASE_URL}/api/inventario{ruta}'


def _ajustar(producto_id, cantidad, motivo='', referencia_pedido=''):
    try:
        respuesta = requests.post(
            _url(f'/productos/{producto_id}/ajustar/'),
            json={'cantidad': cantidad, 'motivo': motivo, 'referencia_pedido': referencia_pedido},
            headers=_cabeceras(),
            timeout=TIEMPO_ESPERA_SEGUNDOS,
            verify=settings.INVENTARIO_VERIFICAR_SSL,
        )
    except requests.RequestException as error:
        logger.error('No se pudo conectar con la API de inventario: %s', error)
        raise ErrorInventario(f'No se pudo conectar con la API de inventario: {error}') from error

    if respuesta.status_code == 409:
        raise StockInsuficiente(respuesta.json().get('error', 'Existencias insuficientes.'))

    if not respuesta.ok:
        logger.error('La API de inventario respondió %s: %s', respuesta.status_code, respuesta.text)
        raise ErrorInventario(f'La API de inventario respondió con un error ({respuesta.status_code}).')

    return respuesta.json()


def descontar_stock(producto_id, cantidad, referencia_pedido=''):
    """Descuenta `cantidad` unidades (una venta). `cantidad` debe ser positiva."""
    if cantidad <= 0:
        raise ValueError('cantidad debe ser un entero positivo.')
    return _ajustar(
        producto_id, -cantidad, motivo='Venta', referencia_pedido=referencia_pedido
    )


def reponer_stock(producto_id, cantidad, motivo='Compensación automática', referencia_pedido=''):
    """Suma `cantidad` unidades (reabastecimiento o compensación). `cantidad` debe ser positiva."""
    if cantidad <= 0:
        raise ValueError('cantidad debe ser un entero positivo.')
    return _ajustar(producto_id, cantidad, motivo=motivo, referencia_pedido=referencia_pedido)


def consultar_stock(producto_id):
    """GET del stock actual de un producto (no modifica nada)."""
    try:
        respuesta = requests.get(
            _url(f'/productos/{producto_id}/'),
            headers=_cabeceras(),
            timeout=TIEMPO_ESPERA_SEGUNDOS,
            verify=settings.INVENTARIO_VERIFICAR_SSL,
        )
        respuesta.raise_for_status()
    except requests.RequestException as error:
        raise ErrorInventario(f'No se pudo consultar el inventario: {error}') from error
    return respuesta.json()
