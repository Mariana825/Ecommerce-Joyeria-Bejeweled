"""Newsletter y correo electrónico: TU-38 a TU-40 (+ extras EX-19 a EX-21)."""

import re
import smtplib
from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from django.core import mail, signing
from django.db import IntegrityError, transaction
from django.urls import reverse

from pedidos.email import enviar_correo_compra
from productos.emails import SAL_BAJA, avisar_nuevo_producto
from productos.models import Suscriptor

pytestmark = pytest.mark.django_db


def _mensajes(respuesta):
    return [str(m) for m in get_messages(respuesta.wsgi_request)]


# ----------------------------------------------------------------- TU-38
def test_tu38_suscribe_un_correo_valido(client):
    respuesta = client.post(reverse('productos:newsletter'), {'email': 'nueva@example.com'})

    assert respuesta.status_code == 302
    assert respuesta.url == reverse('productos:inicio')
    suscriptor = Suscriptor.objects.get()
    assert suscriptor.email == 'nueva@example.com'
    assert suscriptor.activo is True


@pytest.mark.parametrize('invalido', ['', 'sin-arroba', 'a@', '@b.com'])
def test_tu38b_rechaza_correos_invalidos(client, invalido):
    respuesta = client.post(reverse('productos:newsletter'), {'email': invalido})

    assert Suscriptor.objects.count() == 0
    assert any('válido' in m for m in _mensajes(respuesta))


def test_tu38c_regresa_a_la_pagina_indicada(client):
    respuesta = client.post(reverse('productos:newsletter'),
                            {'email': 'nueva@example.com', 'siguiente': '/catalogo/'})

    assert respuesta.url == '/catalogo/'


def test_tu38d_solo_acepta_post(client):
    assert client.get(reverse('productos:newsletter')).status_code == 405


# ----------------------------------------------------------------- TU-39
def test_tu39_no_duplica_suscripciones(client):
    url = reverse('productos:newsletter')
    client.post(url, {'email': 'nueva@example.com'})

    respuesta = client.post(url, {'email': 'NUEVA@Example.com'})   # mismo correo, otra capitalización

    assert Suscriptor.objects.count() == 1
    assert any('ya está suscrito' in m for m in _mensajes(respuesta))


def test_tu39b_la_base_de_datos_impide_correos_repetidos():
    Suscriptor.objects.create(email='nueva@example.com')

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Suscriptor.objects.create(email='nueva@example.com')


def test_tu39c_quien_se_dio_de_baja_puede_volver_a_suscribirse(client):
    Suscriptor.objects.create(email='nueva@example.com', activo=False)

    client.post(reverse('productos:newsletter'), {'email': 'nueva@example.com'})

    assert Suscriptor.objects.count() == 1
    assert Suscriptor.objects.get().activo is True


def test_tu39d_la_baja_con_token_valido_desactiva_la_suscripcion(client):
    Suscriptor.objects.create(email='nueva@example.com')
    token = signing.dumps('nueva@example.com', salt=SAL_BAJA)

    client.get(reverse('productos:newsletter_baja', args=[token]))

    assert Suscriptor.objects.get().activo is False


def test_tu39e_un_token_de_baja_invalido_no_cambia_nada(client):
    Suscriptor.objects.create(email='nueva@example.com')

    respuesta = client.get(reverse('productos:newsletter_baja', args=['token-falso']))

    assert Suscriptor.objects.get().activo is True
    assert any('no es válido' in m for m in _mensajes(respuesta))


# ----------------------------------------------------------------- TU-40
def test_tu40_un_error_de_envio_no_rompe_el_flujo_de_compra(usuario, crear_pedido, producto, caplog):
    pedido = crear_pedido(usuario, [(producto, 1)])

    with patch('pedidos.email.EmailMultiAlternatives.send', side_effect=smtplib.SMTPException('fallo SMTP')):
        resultado = enviar_correo_compra(pedido)

    assert resultado is False
    assert 'No se pudo enviar el correo del pedido' in caplog.text


def test_tu40b_envio_exitoso_de_la_confirmacion(usuario, crear_pedido, producto):
    pedido = crear_pedido(usuario, [(producto, 2)])

    assert enviar_correo_compra(pedido) is True

    assert len(mail.outbox) == 1
    correo = mail.outbox[0]
    assert correo.subject == 'Bejeweled - Pago confirmado'
    assert correo.to == [usuario.email]
    assert correo.alternatives[0][1] == 'text/html'    # también lleva versión HTML


def test_tu40c_sin_usuario_o_sin_correo_no_se_envia_nada(usuario, crear_pedido):
    sin_correo = crear_pedido(usuario)
    usuario.email = ''
    usuario.save()
    sin_usuario = crear_pedido(None)

    assert enviar_correo_compra(sin_correo) is False
    assert enviar_correo_compra(sin_usuario) is False
    assert mail.outbox == []


def test_tu40d_el_aviso_de_nuevo_producto_solo_llega_a_suscriptores_activos(crear_producto):
    Suscriptor.objects.create(email='uno@example.com')
    Suscriptor.objects.create(email='dos@example.com')
    Suscriptor.objects.create(email='baja@example.com', activo=False)
    producto = crear_producto('Anillo Luna')

    avisar_nuevo_producto(producto.pk)

    assert sorted(m.to[0] for m in mail.outbox) == ['dos@example.com', 'uno@example.com']
    primero = mail.outbox[0]
    assert primero.subject == 'Nuevo en Bejeweled: Anillo Luna'
    # Cada correo trae su enlace de baja, firmado para ese suscriptor
    token = re.search(r'/newsletter/baja/([^/\s"]+)/', primero.body).group(1)
    assert signing.loads(token, salt=SAL_BAJA) == primero.to[0]


def test_tu40e_si_el_servidor_de_correo_falla_no_se_lanza_excepcion(crear_producto, caplog):
    Suscriptor.objects.create(email='uno@example.com')
    producto = crear_producto('Anillo Luna')

    with patch('productos.emails.mail.get_connection') as conexion:
        conexion.return_value.send_messages.side_effect = smtplib.SMTPException('fallo SMTP')
        avisar_nuevo_producto(producto.pk)    # no debe lanzar nada

    assert 'No se pudo avisar del producto' in caplog.text


def test_tu40f_un_producto_inexistente_no_lanza_excepcion():
    avisar_nuevo_producto(99999)

    assert mail.outbox == []


# ------------------------------------------------------------------ EXTRAS
def test_ex19_crear_un_producto_activo_programa_el_aviso_a_suscriptores(
        crear_producto, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks() as callbacks:
        crear_producto('Nuevo activo')
    assert len(callbacks) == 1


def test_ex20_un_producto_inactivo_no_programa_aviso(crear_producto, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks() as callbacks:
        crear_producto('Oculto', activo=False)
    assert callbacks == []


@pytest.mark.xfail(
    strict=True,
    reason='BRECHA DE SEGURIDAD (open redirect): el campo "siguiente" se pasa directo a redirect(), '
           'así que un enlace/formulario manipulado puede mandar al usuario a un sitio externo. '
           'Valida con django.utils.http.url_has_allowed_host_and_scheme (aplica también a '
           'alternar_favorito y cambiar_idioma); entonces quita el xfail.',
)
def test_ex21_no_redirige_a_sitios_externos(client):
    respuesta = client.post(reverse('productos:newsletter'),
                            {'email': 'nueva@example.com', 'siguiente': 'https://sitio-malicioso.com/'})

    assert not respuesta.url.startswith('https://sitio-malicioso.com')
