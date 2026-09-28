"""
Endpoints que consume el botón de PayPal (JS SDK) desde el navegador.

Flujo:
    1. El navegador carga el SDK de PayPal con el Client ID público.
    2. Al pulsar el botón, el SDK llama a `crear_orden` (POST, JSON) para
       obtener un ID de orden.
    3. El comprador aprueba el pago en la ventana de PayPal.
    4. El SDK llama a `capturar_orden` (POST, JSON) para confirmar el cobro;
       aquí marcamos el pedido como pagado y guardamos la referencia.
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from pedidos.models import Pedido

from . import paypal

logger = logging.getLogger(__name__)


@login_required
@require_POST
def crear_orden(request, pedido_id):
    pedido = get_object_or_404(
        Pedido, id=pedido_id, usuario=request.user, estado=Pedido.Estado.PENDIENTE_PAGO
    )

    try:
        id_orden = paypal.crear_orden(pedido)
    except paypal.ErrorPayPal as error:
        logger.error('Error creando orden de PayPal para el pedido %s: %s', pedido.id, error)
        return JsonResponse({'error': str(error)}, status=502)

    return JsonResponse({'id': id_orden})


@login_required
@require_POST
def capturar_orden(request, pedido_id):
    pedido = get_object_or_404(
        Pedido,
        id=pedido_id,
        usuario=request.user,
        estado=Pedido.Estado.PENDIENTE_PAGO
    )

    try:
        datos = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Solicitud inválida.'},
            status=400
        )

    id_orden_paypal = datos.get('orderID')

    if not id_orden_paypal:
        return JsonResponse(
            {'error': 'Falta el ID de la orden de PayPal.'},
            status=400
        )

    logger.info(
        'Intentando capturar PayPal | pedido=%s | paypal_order=%s',
        pedido.id,
        id_orden_paypal
    )

    try:
        resultado = paypal.capturar_orden(id_orden_paypal)

    except paypal.ErrorPayPal as error:
        logger.error(
            'Error capturando PayPal | pedido=%s | paypal_order=%s | error=%s',
            pedido.id,
            id_orden_paypal,
            error
        )

        return JsonResponse(
            {'error': str(error)},
            status=502
        )

    logger.info(
        'Respuesta captura PayPal | pedido=%s | respuesta=%s',
        pedido.id,
        resultado
    )

    if resultado.get('status') != 'COMPLETED':
        logger.warning(
            'PayPal no completó la captura | pedido=%s | respuesta=%s',
            pedido.id,
            resultado
        )

        return JsonResponse(
            {
                'error': 'PayPal no pudo completar el pago.',
                'paypal_status': resultado.get('status'),
            },
            status=502
        )

    referencia = paypal.obtener_id_captura(resultado)

    pedido.estado = Pedido.Estado.PAGADO
    pedido.metodo_pago = 'PayPal (Sandbox)'
    pedido.referencia_pago = referencia

    pedido.save(
        update_fields=[
            'estado',
            'metodo_pago',
            'referencia_pago',
            'actualizado'
        ]
    )

    logger.info(
        'Pago completado correctamente | pedido=%s | captura=%s',
        pedido.id,
        referencia
    )

    return JsonResponse({
        'estado': 'pagado',
        'referencia': referencia
    })