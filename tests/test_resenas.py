"""Reseñas de productos: TU-34 a TU-37."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from pedidos.models import Pedido
from productos.forms import ResenaForm
from productos.models import Resena

pytestmark = pytest.mark.django_db


def _publicar(cliente, producto, calificacion=5, comentario='Hermosa pieza'):
    return cliente.post(reverse('productos:crear_resena', args=[producto.id]),
                        {'calificacion': calificacion, 'comentario': comentario})


# ----------------------------------------------------------------- TU-34
def test_tu34_crea_una_resena_valida(cliente_autenticado, usuario, producto, crear_pedido):
    crear_pedido(usuario, [(producto, 1)], estado=Pedido.Estado.PAGADO)

    respuesta = _publicar(cliente_autenticado, producto, calificacion=5, comentario='Hermosa pieza')

    assert respuesta.status_code == 302
    assert respuesta.url == producto.get_absolute_url()
    resena = Resena.objects.get()
    assert (resena.usuario, resena.producto) == (usuario, producto)
    assert resena.calificacion == 5
    assert resena.comentario == 'Hermosa pieza'
    assert resena.aprobada is True


def test_tu34b_el_modelo_acepta_una_resena_valida(usuario, producto):
    Resena(producto=producto, usuario=usuario, calificacion=4, comentario='Muy bonita').full_clean()


def test_tu34c_un_usuario_solo_puede_reseñar_una_vez_cada_producto(
        cliente_autenticado, usuario, producto, crear_pedido):
    crear_pedido(usuario, [(producto, 1)], estado=Pedido.Estado.PAGADO)

    _publicar(cliente_autenticado, producto, 5, 'Primera')
    _publicar(cliente_autenticado, producto, 1, 'Segunda')

    resena = Resena.objects.get()
    assert resena.comentario == 'Primera'    # la segunda se ignora


def test_tu34d_exige_iniciar_sesion(client, producto):
    respuesta = _publicar(client, producto)

    assert respuesta.status_code == 302
    assert reverse('usuarios:login') in respuesta.url
    assert Resena.objects.count() == 0


# ----------------------------------------------------------------- TU-35
@pytest.mark.parametrize('calificacion', [0, 6, -1, 100])
def test_tu35_el_modelo_rechaza_puntuaciones_fuera_de_rango(usuario, producto, calificacion):
    resena = Resena(producto=producto, usuario=usuario, calificacion=calificacion, comentario='x')

    with pytest.raises(ValidationError) as error:
        resena.full_clean()
    assert 'calificacion' in error.value.message_dict


@pytest.mark.parametrize('calificacion', ['0', '6', 'abc', ''])
def test_tu35b_el_formulario_rechaza_puntuaciones_invalidas(calificacion):
    form = ResenaForm({'calificacion': calificacion, 'comentario': 'x'})

    assert not form.is_valid()
    assert 'calificacion' in form.errors


@pytest.mark.parametrize('calificacion', [1, 2, 3, 4, 5])
def test_tu35c_el_formulario_acepta_de_1_a_5(calificacion):
    assert ResenaForm({'calificacion': calificacion, 'comentario': 'x'}).is_valid()


@pytest.mark.parametrize('calificacion', [0, 6])
def test_tu35d_la_vista_no_publica_puntuaciones_fuera_de_rango(
        cliente_autenticado, usuario, producto, crear_pedido, calificacion):
    crear_pedido(usuario, [(producto, 1)], estado=Pedido.Estado.PAGADO)

    _publicar(cliente_autenticado, producto, calificacion)

    assert Resena.objects.count() == 0


# ----------------------------------------------------------------- TU-36
@pytest.mark.xfail(
    strict=True,
    reason='BRECHA DETECTADA: la vista crear_resena no verifica que el usuario haya comprado el '
           'producto (solo la página de detalle oculta el formulario). Cualquiera con sesión puede '
           'publicar con un POST directo. Agrega la misma comprobación de PedidoItem de `detalle` '
           'dentro de crear_resena; entonces quita el xfail.',
)
def test_tu36_impide_publicar_resena_sin_compra_elegible(cliente_autenticado, producto):
    _publicar(cliente_autenticado, producto)

    assert Resena.objects.count() == 0


def test_tu36b_el_formulario_solo_se_ofrece_a_quien_compro_y_pago(
        cliente_autenticado, usuario, producto, crear_pedido):
    url = producto.get_absolute_url()

    sin_compra = cliente_autenticado.get(url)
    assert sin_compra.context['puede_resenar'] is False
    assert sin_compra.context['form_resena'] is None

    crear_pedido(usuario, [(producto, 1)], estado=Pedido.Estado.PENDIENTE_PAGO)
    assert cliente_autenticado.get(url).context['puede_resenar'] is False   # sin pagar no cuenta

    crear_pedido(usuario, [(producto, 1)], estado=Pedido.Estado.CANCELADO)
    assert cliente_autenticado.get(url).context['puede_resenar'] is False

    crear_pedido(usuario, [(producto, 1)], estado=Pedido.Estado.PAGADO)
    pagado = cliente_autenticado.get(url)
    assert pagado.context['puede_resenar'] is True
    assert pagado.context['form_resena'] is not None


def test_tu36c_la_compra_de_otro_usuario_no_habilita_la_resena(
        cliente_autenticado, otro_usuario, producto, crear_pedido):
    crear_pedido(otro_usuario, [(producto, 1)], estado=Pedido.Estado.PAGADO)

    assert cliente_autenticado.get(producto.get_absolute_url()).context['puede_resenar'] is False


@pytest.mark.xfail(
    strict=True,
    reason='BRECHA DETECTADA: `detalle` solo considera elegibles los pedidos en estado "pagado". '
           'En cuanto el pedido avanza a en_proceso/enviado/entregado (el ciclo normal) el cliente '
           'pierde la posibilidad de reseñar. Usa pedido__estado__in=[pagado, en_proceso, enviado, '
           'entregado] en la vista; entonces quita el xfail.',
)
@pytest.mark.parametrize('estado', ['en_proceso', 'enviado', 'entregado'])
def test_tu36d_un_pedido_ya_enviado_o_entregado_tambien_permite_reseñar(
        cliente_autenticado, usuario, producto, crear_pedido, estado):
    crear_pedido(usuario, [(producto, 1)], estado=estado)

    assert cliente_autenticado.get(producto.get_absolute_url()).context['puede_resenar'] is True


# ----------------------------------------------------------------- TU-37
def _resenar(producto, usuario, calificacion, **extra):
    return Resena.objects.create(producto=producto, usuario=usuario, calificacion=calificacion,
                                 comentario='x', **extra)


def test_tu37_calcula_el_promedio_de_calificaciones(producto, crear_usuario):
    for nota in (5, 4, 4):
        _resenar(producto, crear_usuario(), nota)

    assert producto.calificacion_promedio == 4.3     # 13 / 3 = 4.33... redondeado a 1 decimal
    assert producto.total_resenas == 3
    assert len(producto.estrellas_llenas) == 4
    assert len(producto.estrellas_vacias) == 1


def test_tu37b_sin_resenas_el_promedio_es_cero(producto):
    assert producto.calificacion_promedio == 0
    assert producto.total_resenas == 0
    assert len(producto.estrellas_llenas) == 0
    assert len(producto.estrellas_vacias) == 5


def test_tu37c_las_resenas_ocultas_no_cuentan(producto, crear_usuario):
    _resenar(producto, crear_usuario(), 5)
    _resenar(producto, crear_usuario(), 3)
    _resenar(producto, crear_usuario(), 1, aprobada=False)   # moderada: no cuenta

    assert producto.calificacion_promedio == 4.0
    assert producto.total_resenas == 2


def test_tu37d_el_promedio_es_por_producto(producto, crear_producto, crear_usuario):
    otro = crear_producto('Otro')
    _resenar(producto, crear_usuario(), 5)
    _resenar(otro, crear_usuario(), 1)

    assert producto.calificacion_promedio == 5.0
    assert otro.calificacion_promedio == 1.0
