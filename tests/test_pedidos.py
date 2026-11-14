"""Pedidos y checkout: TU-15 a TU-20 (+ extras EX-07 a EX-12)."""

from decimal import Decimal
from unittest.mock import ANY, patch

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from inventario.cliente import ErrorInventario, StockInsuficiente
from pedidos.models import Pedido

pytestmark = pytest.mark.django_db

DESCONTAR = 'pedidos.views.inventario_cliente.descontar_stock'
REPONER = 'pedidos.views.inventario_cliente.reponer_stock'


def _llenar_carrito(client, *items):
    for producto, cantidad in items:
        client.post(reverse('carrito:agregar', args=[producto.id]), {'cantidad': cantidad})


# ----------------------------------------------------------------- TU-15
def test_tu15_checkout_crea_un_pedido_valido(cliente_autenticado, usuario, direccion, crear_producto):
    anillo = crear_producto('Anillo', precio='1000.00', existencias=5)
    collar = crear_producto('Collar', precio='550.00', existencias=5)
    _llenar_carrito(cliente_autenticado, (anillo, 1), (collar, 2))

    with patch(DESCONTAR) as descontar:
        respuesta = cliente_autenticado.post(reverse('pedidos:checkout'), {'direccion_id': direccion.id})

    pedido = Pedido.objects.get()
    assert respuesta.status_code == 302
    assert respuesta.url == reverse('pedidos:pago_pendiente', args=[pedido.pk])
    assert pedido.usuario == usuario
    # La dirección se copia al pedido (queda como "foto" aunque luego se edite)
    assert pedido.nombre_destinatario == direccion.destinatario
    assert pedido.calle == direccion.calle
    assert pedido.codigo_postal == direccion.codigo_postal
    # Artículos del pedido
    assert pedido.items.count() == 2
    assert {(i.nombre_producto, i.cantidad) for i in pedido.items.all()} == {('Anillo', 1), ('Collar', 2)}
    # Se pidió descontar el stock de cada artículo a través de la API
    assert descontar.call_count == 2
    descontar.assert_any_call(anillo.id, 1, referencia_pedido=str(pedido.id))
    descontar.assert_any_call(collar.id, 2, referencia_pedido=str(pedido.id))
    # El carrito queda vacío
    assert cliente_autenticado.session['carrito'] == {}


# ----------------------------------------------------------------- TU-16
def test_tu16_total_del_pedido(usuario, crear_pedido, crear_producto):
    anillo = crear_producto('Anillo', precio='1000.00')
    collar = crear_producto('Collar', precio='550.50')

    pedido = crear_pedido(usuario, [(anillo, 1), (collar, 2)])

    assert pedido.total == Decimal('2101.00')
    assert sum(item.subtotal for item in pedido.items.all()) == pedido.total


def test_tu16b_el_total_usa_el_precio_guardado_no_el_actual(usuario, crear_pedido, crear_producto):
    anillo = crear_producto('Anillo', precio='1000.00')
    pedido = crear_pedido(usuario, [(anillo, 2)])

    anillo.precio = Decimal('9999.00')   # el catálogo sube de precio después de la compra
    anillo.save()

    assert pedido.total == Decimal('2000.00')


def test_tu16c_pedido_sin_articulos_vale_cero(usuario, crear_pedido):
    assert crear_pedido(usuario).total == 0


# ----------------------------------------------------------------- TU-17
def test_tu17_identificador_unico_y_numero_por_usuario(client, usuario, otro_usuario, crear_pedido):
    pedido_ajeno = crear_pedido(otro_usuario)    # id 1
    primero = crear_pedido(usuario)              # id 2
    segundo = crear_pedido(usuario)              # id 3

    assert len({pedido_ajeno.pk, primero.pk, segundo.pk}) == 3
    assert segundo.pk > primero.pk
    assert str(primero) == f'Pedido #{primero.pk} - {usuario}'

    client.force_login(usuario)
    # El número visible es el consecutivo DEL USUARIO, no el id global
    r1 = client.get(reverse('pedidos:detalle', args=[primero.pk]))
    r2 = client.get(reverse('pedidos:detalle', args=[segundo.pk]))
    assert r1.status_code == r2.status_code == 200
    assert r1.context['numero_pedido'] == 1
    assert r2.context['numero_pedido'] == 2


# ----------------------------------------------------------------- TU-18
def test_tu18_estado_inicial_del_pedido(usuario, crear_pedido):
    pedido = crear_pedido(usuario)

    assert pedido.estado == Pedido.Estado.PENDIENTE_PAGO == 'pendiente_pago'
    assert pedido.metodo_pago == ''
    assert pedido.referencia_pago == ''


def test_tu18b_el_pedido_nacido_del_checkout_queda_pendiente_de_pago(
        cliente_autenticado, direccion, producto):
    _llenar_carrito(cliente_autenticado, (producto, 1))

    with patch(DESCONTAR):
        cliente_autenticado.post(reverse('pedidos:checkout'), {'direccion_id': direccion.id})

    assert Pedido.objects.get().estado == Pedido.Estado.PENDIENTE_PAGO


# ----------------------------------------------------------------- TU-19
def test_tu19_rechaza_un_estado_inexistente(usuario, crear_pedido):
    pedido = crear_pedido(usuario)
    pedido.estado = 'estado_inventado'

    with pytest.raises(ValidationError) as error:
        pedido.full_clean()
    assert 'estado' in error.value.message_dict


@pytest.mark.parametrize('estado', ['pagado', 'en_proceso', 'enviado', 'entregado', 'cancelado'])
def test_tu19b_pagos_solo_operan_sobre_pedidos_pendientes_de_pago(
        cliente_autenticado, usuario, crear_pedido, estado):
    pedido = crear_pedido(usuario, estado=estado)

    with patch('pagos.views.paypal.crear_orden') as crear, \
            patch('pagos.views.paypal.capturar_orden') as capturar:
        r_crear = cliente_autenticado.post(reverse('pagos:crear_orden', args=[pedido.pk]))
        r_capturar = cliente_autenticado.post(
            reverse('pagos:capturar_orden', args=[pedido.pk]),
            data='{"orderID": "X"}', content_type='application/json')

    assert r_crear.status_code == 404
    assert r_capturar.status_code == 404
    crear.assert_not_called()
    capturar.assert_not_called()
    pedido.refresh_from_db()
    assert pedido.estado == estado   # no cambió


# ----------------------------------------------------------------- TU-20
def test_tu20_si_falta_stock_se_cancela_el_pedido_y_se_repone_lo_ya_descontado(
        cliente_autenticado, direccion, crear_producto):
    anillo = crear_producto('Anillo', existencias=5)
    collar = crear_producto('Collar', existencias=5)
    _llenar_carrito(cliente_autenticado, (anillo, 2), (collar, 1))

    with patch(DESCONTAR, side_effect=[{'ok': True}, StockInsuficiente('sin stock')]), \
            patch(REPONER) as reponer:
        respuesta = cliente_autenticado.post(reverse('pedidos:checkout'), {'direccion_id': direccion.id})

    pedido = Pedido.objects.get()
    assert pedido.estado == Pedido.Estado.CANCELADO
    assert respuesta.status_code == 302
    assert respuesta.url == reverse('carrito:ver_carrito')
    # Se devolvió únicamente lo que sí se alcanzó a descontar (el anillo)
    reponer.assert_called_once_with(anillo.id, 2, motivo=ANY, referencia_pedido=str(pedido.id))
    # El carrito se conserva para que el cliente pueda reintentar
    assert set(cliente_autenticado.session['carrito']) == {str(anillo.id), str(collar.id)}
    # La tienda no toca existencias directamente: eso lo hace la API de inventario
    anillo.refresh_from_db()
    assert anillo.existencias == 5


def test_tu20b_si_falla_el_primer_articulo_no_hay_nada_que_reponer(
        cliente_autenticado, direccion, producto):
    _llenar_carrito(cliente_autenticado, (producto, 1))

    with patch(DESCONTAR, side_effect=StockInsuficiente('sin stock')), patch(REPONER) as reponer:
        cliente_autenticado.post(reverse('pedidos:checkout'), {'direccion_id': direccion.id})

    assert Pedido.objects.get().estado == Pedido.Estado.CANCELADO
    reponer.assert_not_called()


def test_tu20c_un_error_generico_de_inventario_tambien_cancela_el_pedido(
        cliente_autenticado, direccion, producto):
    _llenar_carrito(cliente_autenticado, (producto, 1))

    with patch(DESCONTAR, side_effect=ErrorInventario('API caída')):
        respuesta = cliente_autenticado.post(reverse('pedidos:checkout'), {'direccion_id': direccion.id})

    assert Pedido.objects.get().estado == Pedido.Estado.CANCELADO
    assert respuesta.url == reverse('carrito:ver_carrito')


def test_tu20d_si_la_compensacion_falla_el_checkout_no_se_rompe(
        cliente_autenticado, direccion, crear_producto):
    a = crear_producto('A', existencias=5)
    b = crear_producto('B', existencias=5)
    _llenar_carrito(cliente_autenticado, (a, 1), (b, 1))

    with patch(DESCONTAR, side_effect=[{'ok': True}, StockInsuficiente('x')]), \
            patch(REPONER, side_effect=ErrorInventario('API caída')):
        respuesta = cliente_autenticado.post(reverse('pedidos:checkout'), {'direccion_id': direccion.id})

    assert respuesta.status_code == 302
    assert Pedido.objects.get().estado == Pedido.Estado.CANCELADO


# ------------------------------------------------------------------ EXTRAS
def test_ex07_checkout_exige_iniciar_sesion(client):
    respuesta = client.get(reverse('pedidos:checkout'))

    assert respuesta.status_code == 302
    assert reverse('usuarios:login') in respuesta.url


def test_ex08_checkout_con_carrito_vacio_redirige_al_catalogo(cliente_autenticado):
    respuesta = cliente_autenticado.get(reverse('pedidos:checkout'))

    assert respuesta.status_code == 302
    assert respuesta.url == reverse('productos:catalogo')


def test_ex09_checkout_verifica_el_stock_antes_de_crear_el_pedido(
        cliente_autenticado, direccion, producto):
    _llenar_carrito(cliente_autenticado, (producto, 5))
    producto.existencias = 2   # otra compra se llevó las piezas mientras tanto
    producto.save()

    with patch(DESCONTAR) as descontar:
        respuesta = cliente_autenticado.post(reverse('pedidos:checkout'), {'direccion_id': direccion.id})

    assert respuesta.url == reverse('carrito:ver_carrito')
    assert Pedido.objects.count() == 0
    descontar.assert_not_called()


def test_ex10_checkout_rechaza_direcciones_de_otro_usuario(
        cliente_autenticado, producto, otro_usuario):
    from usuarios.models import DireccionEnvio
    ajena = DireccionEnvio.objects.create(
        usuario=otro_usuario, destinatario='Otro', calle='Calle 9', ciudad='CDMX',
        estado='CDMX', codigo_postal='06000')
    _llenar_carrito(cliente_autenticado, (producto, 1))

    respuesta = cliente_autenticado.post(reverse('pedidos:checkout'), {'direccion_id': ajena.id})

    assert respuesta.status_code == 404
    assert Pedido.objects.count() == 0


def test_ex11_un_usuario_no_puede_ver_pedidos_de_otro(cliente_autenticado, otro_usuario, crear_pedido):
    pedido_ajeno = crear_pedido(otro_usuario)

    assert cliente_autenticado.get(reverse('pedidos:detalle', args=[pedido_ajeno.pk])).status_code == 404
    assert cliente_autenticado.get(
        reverse('pedidos:pago_pendiente', args=[pedido_ajeno.pk])).status_code == 404


def test_ex12_el_correo_se_envia_solo_al_pasar_a_pagado(
        usuario, crear_pedido, django_capture_on_commit_callbacks):
    with patch('pedidos.signals.enviar_correo_compra') as enviar:
        with django_capture_on_commit_callbacks(execute=True):
            pedido = crear_pedido(usuario)                    # nace pendiente: no envía
        enviar.assert_not_called()

        with django_capture_on_commit_callbacks(execute=True):
            pedido.estado = Pedido.Estado.PAGADO
            pedido.save()                                      # pasa a pagado: envía
        enviar.assert_called_once_with(pedido)

        with django_capture_on_commit_callbacks(execute=True):
            pedido.estado = Pedido.Estado.ENVIADO
            pedido.save()                                      # otros cambios: no reenvía
        assert enviar.call_count == 1
