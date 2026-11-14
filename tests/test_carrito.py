"""Carrito de compras: TU-10 a TU-14."""

from decimal import Decimal

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory
from django.urls import reverse

from carrito.carrito import Carrito

pytestmark = pytest.mark.django_db


def _nuevo_carrito():
    """Carrito sobre una sesión vacía, sin pasar por el servidor."""
    request = RequestFactory().get('/')
    request.session = SessionStore()
    return Carrito(request)


# ----------------------------------------------------------------- TU-10
def test_tu10_subtotal_de_un_producto(crear_producto):
    producto = crear_producto(precio='250.50', existencias=10)
    carrito = _nuevo_carrito()

    carrito.agregar(producto, cantidad=3)
    items = list(carrito)

    assert len(items) == 1
    assert items[0]['producto'] == producto
    assert items[0]['precio'] == Decimal('250.50')
    assert items[0]['cantidad'] == 3
    assert items[0]['subtotal'] == Decimal('751.50')


# ----------------------------------------------------------------- TU-11
def test_tu11_total_de_varios_productos(crear_producto):
    a = crear_producto('A', precio='19.99', existencias=10)
    b = crear_producto('B', precio='5.01', existencias=10)
    carrito = _nuevo_carrito()

    carrito.agregar(a, cantidad=3)   # 59.97
    carrito.agregar(b, cantidad=2)   # 10.02

    assert carrito.total() == Decimal('69.99')   # exacto, sin errores de punto flotante
    assert len(carrito) == 5                      # unidades totales
    assert sum(item['subtotal'] for item in carrito) == Decimal('69.99')


def test_tu11b_carrito_vacio_tiene_total_cero():
    carrito = _nuevo_carrito()

    assert carrito.total() == Decimal('0')
    assert len(carrito) == 0
    assert list(carrito) == []


def test_tu11c_agregar_el_mismo_producto_acumula_cantidad(crear_producto):
    producto = crear_producto(precio='100.00', existencias=10)
    carrito = _nuevo_carrito()

    carrito.agregar(producto, cantidad=2)
    carrito.agregar(producto, cantidad=3)

    assert carrito.carrito[str(producto.id)]['cantidad'] == 5
    assert carrito.total() == Decimal('500.00')


# ----------------------------------------------------------------- TU-12
@pytest.mark.parametrize('cantidad', [0, -1, -10])
def test_tu12_cantidad_cero_o_negativa_no_agrega_el_producto(crear_producto, cantidad):
    producto = crear_producto(existencias=10)
    carrito = _nuevo_carrito()

    carrito.agregar(producto, cantidad=cantidad)

    assert str(producto.id) not in carrito.carrito
    assert len(carrito) == 0
    assert list(carrito) == []


def test_tu12b_reemplazar_por_cero_elimina_el_producto(crear_producto):
    producto = crear_producto(existencias=10)
    carrito = _nuevo_carrito()
    carrito.agregar(producto, cantidad=2)

    carrito.agregar(producto, cantidad=0, reemplazar_cantidad=True)

    assert str(producto.id) not in carrito.carrito


@pytest.mark.parametrize('valor', ['0', '-4', 'abc', ''])
def test_tu12c_la_vista_normaliza_cantidades_invalidas_a_una_unidad(client, crear_producto, valor):
    producto = crear_producto(existencias=5)

    respuesta = client.post(reverse('carrito:agregar', args=[producto.id]), {'cantidad': valor})

    assert respuesta.status_code == 302
    assert client.session['carrito'][str(producto.id)]['cantidad'] == 1


# ----------------------------------------------------------------- TU-13
def test_tu13_cantidad_superior_al_stock_se_limita_a_las_existencias(crear_producto):
    producto = crear_producto(existencias=3)
    carrito = _nuevo_carrito()

    carrito.agregar(producto, cantidad=10)
    assert carrito.carrito[str(producto.id)]['cantidad'] == 3

    carrito.agregar(producto, cantidad=1)   # sumar más tampoco pasa del stock
    assert carrito.carrito[str(producto.id)]['cantidad'] == 3


def test_tu13b_actualizar_por_encima_del_stock_tambien_se_limita(client, crear_producto):
    producto = crear_producto(existencias=4)
    client.post(reverse('carrito:agregar', args=[producto.id]), {'cantidad': 1})

    client.post(reverse('carrito:actualizar', args=[producto.id]), {'cantidad': 99})

    assert client.session['carrito'][str(producto.id)]['cantidad'] == 4


def test_tu13c_producto_agotado_no_se_puede_agregar(client, crear_producto):
    producto = crear_producto(existencias=0)

    respuesta = client.post(reverse('carrito:agregar', args=[producto.id]), {'cantidad': 1})

    assert respuesta.status_code == 302
    assert respuesta.url == producto.get_absolute_url()
    assert client.session.get('carrito', {}) == {}


def test_tu13d_producto_inactivo_devuelve_404(client, crear_producto):
    producto = crear_producto(activo=False)

    respuesta = client.post(reverse('carrito:agregar', args=[producto.id]), {'cantidad': 1})

    assert respuesta.status_code == 404


# ----------------------------------------------------------------- TU-14
def test_tu14_recalcula_el_total_al_modificar_una_cantidad(crear_producto):
    a = crear_producto('A', precio='100.00', existencias=10)
    b = crear_producto('B', precio='50.00', existencias=10)
    carrito = _nuevo_carrito()
    carrito.agregar(a, cantidad=2)
    carrito.agregar(b, cantidad=1)
    assert carrito.total() == Decimal('250.00')

    carrito.agregar(a, cantidad=4, reemplazar_cantidad=True)
    assert carrito.total() == Decimal('450.00')

    carrito.eliminar(b)
    assert carrito.total() == Decimal('400.00')


def test_tu14b_la_vista_actualizar_cambia_la_cantidad_guardada(client, crear_producto):
    producto = crear_producto(precio='100.00', existencias=10)
    client.post(reverse('carrito:agregar', args=[producto.id]), {'cantidad': 1})

    client.post(reverse('carrito:actualizar', args=[producto.id]), {'cantidad': 3})

    assert client.session['carrito'][str(producto.id)]['cantidad'] == 3


def test_tu14c_la_vista_eliminar_quita_el_producto(client, crear_producto):
    producto = crear_producto(existencias=10)
    client.post(reverse('carrito:agregar', args=[producto.id]), {'cantidad': 2})

    client.post(reverse('carrito:eliminar', args=[producto.id]))

    assert str(producto.id) not in client.session['carrito']
