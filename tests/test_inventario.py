"""Inventario: TU-21 a TU-24 (+ extras EX-13, EX-14)."""

from unittest.mock import ANY, patch

import pytest
import requests
from django.conf import settings as django_settings
from django.urls import reverse
from rest_framework.test import APIClient

from inventario.cliente import (ErrorInventario, StockInsuficiente, descontar_stock,
                                reponer_stock)
from inventario.models import MovimientoInventario


def _url(producto):
    return reverse('inventario:ajustar_stock', args=[producto.id])


# ----------------------------------------------------------------- TU-21
@pytest.mark.django_db
def test_tu21_reserva_descuenta_existencias_disponibles(api_cliente, crear_producto):
    producto = crear_producto(existencias=10)

    respuesta = api_cliente.post(
        _url(producto), {'cantidad': -3, 'motivo': 'Venta', 'referencia_pedido': '77'}, format='json')

    assert respuesta.status_code == 200
    assert respuesta.json() == {'producto_id': producto.id, 'existencias': 7,
                                'disponible': True, 'movimiento_id': ANY}
    producto.refresh_from_db()
    assert producto.existencias == 7
    movimiento = MovimientoInventario.objects.get()
    assert movimiento.tipo == MovimientoInventario.Tipo.SALIDA
    assert movimiento.cantidad == -3
    assert movimiento.existencias_resultantes == 7
    assert movimiento.referencia_pedido == '77'


@pytest.mark.django_db
def test_tu21b_se_puede_reservar_exactamente_todo_el_stock(api_cliente, crear_producto):
    producto = crear_producto(existencias=2)

    respuesta = api_cliente.post(_url(producto), {'cantidad': -2}, format='json')

    assert respuesta.status_code == 200
    assert respuesta.json()['existencias'] == 0
    assert respuesta.json()['disponible'] is False


# ----------------------------------------------------------------- TU-22
@pytest.mark.django_db
def test_tu22_rechaza_una_reserva_superior_al_stock(api_cliente, crear_producto):
    producto = crear_producto(existencias=3)

    respuesta = api_cliente.post(_url(producto), {'cantidad': -5}, format='json')

    assert respuesta.status_code == 409
    assert respuesta.json()['existencias_actuales'] == 3
    assert respuesta.json()['cantidad_solicitada'] == -5
    producto.refresh_from_db()
    assert producto.existencias == 3                     # no cambió
    assert MovimientoInventario.objects.count() == 0     # y no quedó movimiento


# ----------------------------------------------------------------- TU-23
@pytest.mark.django_db
def test_tu23_liberar_una_reserva_devuelve_las_existencias(api_cliente, crear_producto):
    producto = crear_producto(existencias=10)
    api_cliente.post(_url(producto), {'cantidad': -4}, format='json')   # reserva

    respuesta = api_cliente.post(
        _url(producto), {'cantidad': 4, 'motivo': 'Compensación'}, format='json')   # liberación

    assert respuesta.status_code == 200
    producto.refresh_from_db()
    assert producto.existencias == 10
    tipos = list(MovimientoInventario.objects.order_by('id').values_list('tipo', 'cantidad'))
    assert tipos == [('salida', -4), ('entrada', 4)]


@pytest.mark.django_db
def test_tu23b_cantidad_cero_es_invalida(api_cliente, crear_producto):
    producto = crear_producto(existencias=10)

    respuesta = api_cliente.post(_url(producto), {'cantidad': 0}, format='json')

    assert respuesta.status_code == 400
    assert MovimientoInventario.objects.count() == 0


@pytest.mark.django_db
def test_tu23c_producto_inexistente_devuelve_404(api_cliente):
    respuesta = api_cliente.post(
        reverse('inventario:ajustar_stock', args=[99999]), {'cantidad': 1}, format='json')

    assert respuesta.status_code == 404


# ----------------------------------------------------------------- TU-24
def test_tu24_el_cliente_lanza_stock_insuficiente_ante_un_409(fabrica_respuesta):
    respuesta = fabrica_respuesta(409, {'error': 'No hay existencias suficientes para esta salida.'})

    with patch('inventario.cliente.requests.post', return_value=respuesta) as post:
        with pytest.raises(StockInsuficiente, match='No hay existencias suficientes'):
            descontar_stock(1, 2, referencia_pedido='9')

    args, kwargs = post.call_args
    assert args[0].endswith('/api/inventario/productos/1/ajustar/')
    assert kwargs['json'] == {'cantidad': -2, 'motivo': 'Venta', 'referencia_pedido': '9'}
    assert kwargs['headers'] == {'X-API-Key': django_settings.INVENTARIO_API_KEY}
    assert kwargs['timeout'] > 0     # nunca debe quedarse esperando para siempre


def test_tu24b_stock_insuficiente_es_un_tipo_de_error_de_inventario():
    assert issubclass(StockInsuficiente, ErrorInventario)


def test_tu24c_un_error_500_es_error_de_inventario_pero_no_stock_insuficiente(fabrica_respuesta):
    respuesta = fabrica_respuesta(500, texto='boom')

    with patch('inventario.cliente.requests.post', return_value=respuesta):
        with pytest.raises(ErrorInventario) as error:
            descontar_stock(1, 1)

    assert not isinstance(error.value, StockInsuficiente)
    assert '500' in str(error.value)


@pytest.mark.parametrize('excepcion', [requests.ConnectionError('sin red'), requests.Timeout('lento')])
def test_tu24d_los_fallos_de_red_se_convierten_en_error_de_inventario(excepcion):
    with patch('inventario.cliente.requests.post', side_effect=excepcion):
        with pytest.raises(ErrorInventario, match='No se pudo conectar'):
            descontar_stock(1, 1)


@pytest.mark.parametrize('funcion', [descontar_stock, reponer_stock])
@pytest.mark.parametrize('cantidad', [0, -3])
def test_tu24e_cantidades_no_positivas_se_rechazan_antes_de_llamar_a_la_api(funcion, cantidad):
    with patch('inventario.cliente.requests.post') as post:
        with pytest.raises(ValueError):
            funcion(1, cantidad)
    post.assert_not_called()


def test_tu24f_reponer_envia_una_cantidad_positiva(fabrica_respuesta):
    respuesta = fabrica_respuesta(200, {'existencias': 12})

    with patch('inventario.cliente.requests.post', return_value=respuesta) as post:
        resultado = reponer_stock(1, 4, referencia_pedido='9')

    assert resultado == {'existencias': 12}
    assert post.call_args.kwargs['json']['cantidad'] == 4


# ------------------------------------------------------------------ EXTRAS
@pytest.mark.django_db
@pytest.mark.parametrize('encabezados', [{}, {'HTTP_X_API_KEY': 'clave-incorrecta'}])
def test_ex13_la_api_exige_la_clave_correcta(crear_producto, encabezados):
    producto = crear_producto(existencias=10)
    cliente = APIClient()
    cliente.credentials(**encabezados)

    respuesta = cliente.post(_url(producto), {'cantidad': -1}, format='json')

    assert respuesta.status_code == 403
    producto.refresh_from_db()
    assert producto.existencias == 10


@pytest.mark.django_db
def test_ex14_si_no_hay_clave_configurada_la_api_queda_cerrada(crear_producto, settings):
    settings.INVENTARIO_API_KEY = ''
    producto = crear_producto(existencias=10)
    cliente = APIClient()
    cliente.credentials(HTTP_X_API_KEY='')

    respuesta = cliente.post(_url(producto), {'cantidad': -1}, format='json')

    assert respuesta.status_code == 403
