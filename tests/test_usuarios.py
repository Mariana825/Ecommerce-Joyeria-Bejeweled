"""Usuarios y autenticación: TU-01 a TU-05 (+ extras EX-01, EX-02)."""

import re
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from usuarios.forms import RegistroForm
from usuarios.models import DireccionEnvio, Perfil

User = get_user_model()

pytestmark = pytest.mark.django_db

CLAVE = 'Clave-segura-2026'
DATOS_REGISTRO = {
    'username': 'mariana', 'first_name': 'Mariana', 'last_name': 'López',
    'email': 'mariana@example.com', 'password1': CLAVE, 'password2': CLAVE,
}


# ----------------------------------------------------------------- TU-01
def test_tu01_registro_con_datos_validos(client):
    respuesta = client.post(reverse('usuarios:registro'), DATOS_REGISTRO)

    assert respuesta.status_code == 302
    assert respuesta.url == reverse('productos:catalogo')
    usuario = User.objects.get(username='mariana')
    assert usuario.email == 'mariana@example.com'
    assert usuario.first_name == 'Mariana'
    assert Perfil.objects.filter(usuario=usuario).exists()
    # Tras registrarse queda con la sesión iniciada
    assert client.session['_auth_user_id'] == str(usuario.pk)


def test_tu01b_formulario_valido_acepta_datos_correctos():
    assert RegistroForm(DATOS_REGISTRO).is_valid()


@pytest.mark.parametrize('campo', ['username', 'first_name', 'email', 'password1'])
def test_tu01c_campos_obligatorios(campo):
    datos = {**DATOS_REGISTRO, campo: ''}
    form = RegistroForm(datos)
    assert not form.is_valid()
    assert campo in form.errors


def test_tu01d_contrasenas_distintas_son_rechazadas():
    form = RegistroForm({**DATOS_REGISTRO, 'password2': 'Otra-clave-2026'})
    assert not form.is_valid()
    assert 'password2' in form.errors


# ----------------------------------------------------------------- TU-02
def test_tu02_rechaza_username_duplicado(usuario):
    form = RegistroForm({**DATOS_REGISTRO, 'username': usuario.username,
                         'email': 'distinto@example.com'})

    assert not form.is_valid()
    assert 'username' in form.errors
    assert User.objects.filter(username=usuario.username).count() == 1


def test_tu02b_rechaza_correo_duplicado(usuario):
    form = RegistroForm({**DATOS_REGISTRO, 'email': usuario.email})

    assert not form.is_valid()
    assert 'email' in form.errors


def test_tu02c_la_vista_no_crea_segundo_usuario_con_mismo_username(client, usuario):
    respuesta = client.post(reverse('usuarios:registro'),
                            {**DATOS_REGISTRO, 'username': usuario.username})

    assert respuesta.status_code == 200  # vuelve a mostrar el formulario con errores
    assert User.objects.count() == 1


# ----------------------------------------------------------------- TU-03
def test_tu03_la_contrasena_se_guarda_con_hash(settings):
    # Se activa el hasher real de Django (por defecto en producción) en vez del rápido de pruebas.
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.PBKDF2PasswordHasher']

    form = RegistroForm(DATOS_REGISTRO)
    assert form.is_valid()
    usuario = form.save()
    usuario.refresh_from_db()

    assert usuario.password != CLAVE
    assert CLAVE not in usuario.password
    assert usuario.password.startswith('pbkdf2_sha256$')
    assert usuario.check_password(CLAVE)
    assert not usuario.check_password('otra-clave')


# ----------------------------------------------------------------- TU-04
def test_tu04_genera_token_valido_de_recuperacion(usuario):
    token = default_token_generator.make_token(usuario)

    assert token
    assert default_token_generator.check_token(usuario, token)


def test_tu04b_el_flujo_envia_correo_con_enlace_que_funciona(client, usuario):
    respuesta = client.post(reverse('usuarios:password_reset'), {'email': usuario.email})

    assert respuesta.status_code == 302
    assert len(mail.outbox) == 1
    correo = mail.outbox[0]
    assert correo.to == [usuario.email]

    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    coincidencia = re.search(r'/cuenta/contrasena/reset/(?P<uid>[^/\s]+)/(?P<token>[^/\s]+)/', correo.body)
    assert coincidencia, 'El correo no contiene el enlace de recuperación'
    assert coincidencia.group('uid') == uid
    assert default_token_generator.check_token(usuario, coincidencia.group('token'))

    # El enlace es válido: Django redirige al formulario para escribir la nueva contraseña.
    enlace = reverse('usuarios:password_reset_confirm', args=[uid, coincidencia.group('token')])
    assert client.get(enlace).status_code == 302


def test_tu04c_correo_inexistente_no_envia_nada(client):
    respuesta = client.post(reverse('usuarios:password_reset'), {'email': 'nadie@example.com'})

    assert respuesta.status_code == 302  # no revela si la cuenta existe
    assert mail.outbox == []


# ----------------------------------------------------------------- TU-05
def test_tu05_rechaza_token_invalido_o_alterado(usuario):
    token_valido = default_token_generator.make_token(usuario)

    assert not default_token_generator.check_token(usuario, 'token-inventado')
    assert not default_token_generator.check_token(usuario, '')
    assert not default_token_generator.check_token(usuario, token_valido + 'x')


def test_tu05b_rechaza_token_expirado(usuario, settings):
    token = default_token_generator.make_token(usuario)
    despues_del_limite = datetime.now() + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT + 60)

    with patch.object(default_token_generator, '_now', return_value=despues_del_limite):
        assert not default_token_generator.check_token(usuario, token)


def test_tu05c_el_token_se_invalida_al_cambiar_la_contrasena(usuario):
    token = default_token_generator.make_token(usuario)
    usuario.set_password('Nueva-clave-2026')
    usuario.save()

    assert not default_token_generator.check_token(usuario, token)


def test_tu05d_la_vista_marca_enlace_invalido(client, usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    respuesta = client.get(reverse('usuarios:password_reset_confirm', args=[uid, 'abc-invalido']))

    assert respuesta.status_code == 200
    assert respuesta.context['validlink'] is False


# ------------------------------------------------------------------ EXTRAS
def test_ex01_al_crear_un_usuario_se_crea_su_perfil(usuario):
    assert Perfil.objects.filter(usuario=usuario).count() == 1
    assert usuario.perfil.usuario == usuario


def test_ex02_solo_una_direccion_predeterminada_por_usuario(usuario):
    datos = dict(usuario=usuario, destinatario='Ana', calle='Calle 1', ciudad='CDMX',
                 estado='CDMX', codigo_postal='06000')
    primera = DireccionEnvio.objects.create(predeterminada=True, **datos)
    segunda = DireccionEnvio.objects.create(predeterminada=True, **datos)

    primera.refresh_from_db()
    assert primera.predeterminada is False
    assert segunda.predeterminada is True
