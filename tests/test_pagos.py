"""Pagos con PayPal: TU-25 a TU-28 (+ extra EX-15). Todo con mocks: nunca se contacta a PayPal."""

import json
from unittest.mock import patch

import pytest
import requests
from django.core.cache import cache
from django.urls import reverse

from pagos import paypal
from pagos.paypal import ErrorPayPal
from pedidos.models import Pedido

RESPUESTA_CAPTURA = {
    'id': 'ORDEN-1',
    'status': 'COMPLETED',
    'purchase_units': [{'payments': {'captures': [{'id': 'CAP-999', 'status': 'COMPLETED'}]}}],
}


# ----------------------------------------------------------------- TU-25
@pytest.mark.django_db
@pytest.mark.parametrize('moneda', ['USD', 'MXN'])
def test_tu25_la_solicitud_de_pago_lleva_importe_y_moneda_correctos(
        usuario, crear_pedido, crear_producto, settings, moneda):
    settings.PAYPAL_CURRENCY = moneda
    pedido = crear_pedido(usuario, [(crear_producto('A', precio='1000.00'), 2),
                                    (crear_producto('B', precio='550.50'), 1)])

    with patch('pagos.paypal._peticion', return_value={'id': 'ORDEN-123'}) as peticion:
        id_orden = paypal.crear_orden(pedido)

    assert id_orden == 'ORDEN-123'
    metodo, ruta, cuerpo = peticion.call_args.args
    assert (metodo, ruta) == ('POST', '/v2/checkout/orders')
    assert cuerpo['intent'] == 'CAPTURE'
    unidad = cuerpo['purchase_units'][0]
    assert unidad['amount'] == {'currency_code': moneda, 'value': '2550.50'}   # 2*1000 + 550.50
    assert unidad['reference_id'] == str(pedido.id)


@pytest.mark.django_db
def test_tu25b_el_importe_siempre_lleva_dos_decimales_y_sin_separador_de_miles(
        usuario, crear_pedido, crear_producto):
    pedido = crear_pedido(usuario, [(crear_producto(precio='12345.5'), 1)])

    with patch('pagos.paypal._peticion', return_value={'id': 'X'}) as peticion:
        paypal.crear_orden(pedido)

    assert peticion.call_args.args[2]['purchase_units'][0]['amount']['value'] == '12345.50'


def test_tu25c_la_peticion_http_lleva_token_url_y_cuerpo_correctos(fabrica_respuesta):
    respuesta = fabrica_respuesta(201, {'id': 'ORDEN-123'})
    cuerpo = {'intent': 'CAPTURE'}

    with patch('pagos.paypal.obtener_token_acceso', return_value='TOKEN-ABC'), \
            patch('pagos.paypal.requests.request', return_value=respuesta) as peticion:
        resultado = paypal._peticion('POST', '/v2/checkout/orders', cuerpo)

    assert resultado == {'id': 'ORDEN-123'}
    args, kwargs = peticion.call_args
    assert args == ('POST', 'https://api-m.sandbox.paypal.com/v2/checkout/orders')
    assert kwargs['headers']['Authorization'] == 'Bearer TOKEN-ABC'
    assert kwargs['json'] == cuerpo


# ----------------------------------------------------------------- TU-26
def test_tu26_extrae_el_id_de_la_captura():
    assert paypal.obtener_id_captura(RESPUESTA_CAPTURA) == 'CAP-999'


@pytest.mark.parametrize('respuesta, esperado', [
    ({'id': 'ORDEN-1'}, 'ORDEN-1'),       # sin detalle de captura: usa el id de la orden
    ({'purchase_units': []}, ''),         # estructura incompleta: no revienta
    ({}, ''),
])
def test_tu26b_id_de_captura_con_respuestas_incompletas(respuesta, esperado):
    assert paypal.obtener_id_captura(respuesta) == esperado


def test_tu26c_capturar_orden_devuelve_la_respuesta_simulada_de_paypal(fabrica_respuesta):
    respuesta = fabrica_respuesta(201, RESPUESTA_CAPTURA)

    with patch('pagos.paypal.obtener_token_acceso', return_value='T'), \
            patch('pagos.paypal.requests.request', return_value=respuesta) as peticion:
        resultado = paypal.capturar_orden('ORDEN-1')

    assert resultado == RESPUESTA_CAPTURA
    assert peticion.call_args.args[1].endswith('/v2/checkout/orders/ORDEN-1/capture')


def test_tu26d_el_token_de_acceso_se_cachea(fabrica_respuesta):
    respuesta = fabrica_respuesta(200, {'access_token': 'ABC', 'expires_in': 3600})

    with patch('pagos.paypal.requests.post', return_value=respuesta) as post:
        assert paypal.obtener_token_acceso() == 'ABC'
        assert paypal.obtener_token_acceso() == 'ABC'

    assert post.call_count == 1   # la segunda vez salió de la caché


# ----------------------------------------------------------------- TU-27
def test_tu27_un_error_http_de_paypal_lanza_error_paypal(fabrica_respuesta):
    respuesta = fabrica_respuesta(422, texto='UNPROCESSABLE')

    with patch('pagos.paypal.obtener_token_acceso', return_value='T'), \
            patch('pagos.paypal.requests.request', return_value=respuesta):
        with pytest.raises(ErrorPayPal, match='422'):
            paypal._peticion('POST', '/v2/checkout/orders', {})


def test_tu27b_un_fallo_de_conexion_lanza_error_paypal():
    with patch('pagos.paypal.obtener_token_acceso', return_value='T'), \
            patch('pagos.paypal.requests.request', side_effect=requests.ConnectionError('sin red')):
        with pytest.raises(ErrorPayPal, match='No se pudo conectar'):
            paypal._peticion('POST', '/v2/checkout/orders', {})


@pytest.mark.parametrize('error', [requests.Timeout('lento'), ValueError('json roto')])
def test_tu27c_un_fallo_de_autenticacion_lanza_error_paypal_y_no_cachea(error):
    with patch('pagos.paypal.requests.post', side_effect=error):
        with pytest.raises(ErrorPayPal, match='autenticar'):
            paypal.obtener_token_acceso()

    assert cache.get(paypal.CLAVE_CACHE_TOKEN) is None


@pytest.mark.django_db
def test_tu27d_la_vista_responde_502_si_paypal_falla_al_crear_la_orden(
        cliente_autenticado, usuario, crear_pedido):
    pedido = crear_pedido(usuario)

    with patch('pagos.views.paypal.crear_orden', side_effect=ErrorPayPal('PayPal caído')):
        respuesta = cliente_autenticado.post(reverse('pagos:crear_orden', args=[pedido.pk]))

    assert respuesta.status_code == 502
    assert respuesta.json() == {'error': 'PayPal caído'}


@pytest.mark.django_db
def test_tu27e_la_vista_devuelve_el_id_de_la_orden_creada(cliente_autenticado, usuario, crear_pedido):
    pedido = crear_pedido(usuario)

    with patch('pagos.views.paypal.crear_orden', return_value='ORDEN-123'):
        respuesta = cliente_autenticado.post(reverse('pagos:crear_orden', args=[pedido.pk]))

    assert respuesta.status_code == 200
    assert respuesta.json() == {'id': 'ORDEN-123'}


# ----------------------------------------------------------------- TU-28
def _capturar(cliente, pedido, cuerpo='{"orderID": "ORDEN-1"}'):
    return cliente.post(reverse('pagos:capturar_orden', args=[pedido.pk]),
                        data=cuerpo, content_type='application/json')


@pytest.mark.django_db
def test_tu28_el_pedido_pasa_a_pagado_cuando_paypal_confirma(cliente_autenticado, usuario, crear_pedido):
    pedido = crear_pedido(usuario)

    with patch('pagos.views.paypal.capturar_orden', return_value=RESPUESTA_CAPTURA) as capturar:
        respuesta = _capturar(cliente_autenticado, pedido)

    assert respuesta.status_code == 200
    assert respuesta.json() == {'estado': 'pagado', 'referencia': 'CAP-999'}
    capturar.assert_called_once_with('ORDEN-1')
    pedido.refresh_from_db()
    assert pedido.estado == Pedido.Estado.PAGADO
    assert pedido.metodo_pago == 'PayPal (Sandbox)'
    assert pedido.referencia_pago == 'CAP-999'


@pytest.mark.django_db
@pytest.mark.parametrize('estado_paypal', ['PENDING', 'DECLINED', 'FAILED', None])
def test_tu28b_no_se_marca_pagado_si_paypal_no_completa_la_captura(
        cliente_autenticado, usuario, crear_pedido, estado_paypal):
    pedido = crear_pedido(usuario)

    with patch('pagos.views.paypal.capturar_orden', return_value={'status': estado_paypal}):
        respuesta = _capturar(cliente_autenticado, pedido)

    assert respuesta.status_code == 502
    pedido.refresh_from_db()
    assert pedido.estado == Pedido.Estado.PENDIENTE_PAGO
    assert pedido.referencia_pago == ''


@pytest.mark.django_db
def test_tu28c_no_se_marca_pagado_si_paypal_devuelve_un_error(cliente_autenticado, usuario, crear_pedido):
    pedido = crear_pedido(usuario)

    with patch('pagos.views.paypal.capturar_orden', side_effect=ErrorPayPal('falló')):
        respuesta = _capturar(cliente_autenticado, pedido)

    assert respuesta.status_code == 502
    pedido.refresh_from_db()
    assert pedido.estado == Pedido.Estado.PENDIENTE_PAGO


@pytest.mark.django_db
@pytest.mark.parametrize('cuerpo', ['{no es json', '{}', '{"orderID": ""}'])
def test_tu28d_solicitudes_invalidas_devuelven_400_sin_llamar_a_paypal(
        cliente_autenticado, usuario, crear_pedido, cuerpo):
    pedido = crear_pedido(usuario)

    with patch('pagos.views.paypal.capturar_orden') as capturar:
        respuesta = _capturar(cliente_autenticado, pedido, cuerpo)

    assert respuesta.status_code == 400
    capturar.assert_not_called()
    pedido.refresh_from_db()
    assert pedido.estado == Pedido.Estado.PENDIENTE_PAGO


@pytest.mark.django_db
def test_tu28e_no_se_puede_pagar_el_pedido_de_otro_usuario(
        cliente_autenticado, otro_usuario, crear_pedido):
    pedido_ajeno = crear_pedido(otro_usuario)

    with patch('pagos.views.paypal.capturar_orden') as capturar:
        respuesta = _capturar(cliente_autenticado, pedido_ajeno)

    assert respuesta.status_code == 404
    capturar.assert_not_called()


@pytest.mark.django_db
def test_tu28f_exige_sesion_y_metodo_post(client, cliente_autenticado, usuario, crear_pedido):
    pedido = crear_pedido(usuario)
    url = reverse('pagos:capturar_orden', args=[pedido.pk])

    assert cliente_autenticado.get(url).status_code == 405   # solo POST

    cliente_autenticado.logout()
    anonimo = cliente_autenticado.post(url, data='{}', content_type='application/json')
    assert anonimo.status_code == 302
    assert reverse('usuarios:login') in anonimo.url


# ------------------------------------------------------------------ EXTRAS
@pytest.mark.django_db
def test_ex15_el_pago_exitoso_programa_el_correo_de_confirmacion(
        cliente_autenticado, usuario, crear_pedido, django_capture_on_commit_callbacks):
    pedido = crear_pedido(usuario)

    with patch('pedidos.signals.enviar_correo_compra') as enviar, \
            patch('pagos.views.paypal.capturar_orden', return_value=RESPUESTA_CAPTURA):
        with django_capture_on_commit_callbacks(execute=True):
            _capturar(cliente_autenticado, pedido)

    enviar.assert_called_once()
