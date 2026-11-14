"""Chatbot Gemini: TU-29 a TU-31 (+ extras EX-16, EX-17). Gemini siempre va mockeado."""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings as django_settings
from django.urls import reverse
from google.genai import errors as genai_errors

from chatbot import services
from chatbot.models import Mensaje

pytestmark = pytest.mark.django_db


@pytest.fixture
def gemini():
    """Cliente de Gemini falso: `gemini.models.generate_content` es un mock configurable."""
    falso = MagicMock()
    with patch('chatbot.services._obtener_cliente', return_value=falso):
        yield falso


def _historial(texto='Hola'):
    return [{'role': 'user', 'content': texto}]


# ----------------------------------------------------------------- TU-29
def test_tu29_el_prompt_incluye_el_idioma_seleccionado():
    nombre = dict(django_settings.IDIOMAS_DISPONIBLES)['en']

    prompt_en = services._system_prompt('en')
    prompt_es = services._system_prompt('es')

    assert f'responde siempre en {nombre}' in prompt_en
    assert '(código "en")' in prompt_en
    assert 'responde siempre en' not in prompt_es      # español es el idioma base
    assert 'Eres el asistente virtual de Bejeweled' in prompt_es


def test_tu29b_un_codigo_de_idioma_desconocido_usa_el_codigo_tal_cual():
    assert 'responde siempre en xx' in services._system_prompt('xx')


def test_tu29c_el_catalogo_solo_incluye_activos_y_marca_los_agotados(crear_producto):
    disponible = crear_producto('Anillo Luna', precio='1500.00', existencias=3)
    agotado = crear_producto('Collar Sol', existencias=0)
    crear_producto('Pieza Oculta', activo=False)

    prompt = services._system_prompt('es')

    assert f'ID: {disponible.id} | Nombre: Anillo Luna' in prompt
    assert 'Precio: $1500.00 MXN' in prompt
    assert 'Estado: DISPONIBLE' in prompt
    assert f'ID: {agotado.id} | Nombre: Collar Sol' in prompt
    assert 'Estado: AGOTADO' in prompt
    assert 'Pieza Oculta' not in prompt


def test_tu29d_catalogo_vacio_se_indica_explicitamente():
    assert 'no hay productos activos' in services._contexto_catalogo()


# ----------------------------------------------------------------- TU-30
def test_tu30_procesa_una_respuesta_simulada_de_gemini(gemini, respuesta_gemini, crear_producto):
    p1 = crear_producto('Anillo Luna', precio='1500.00')
    p2 = crear_producto('Collar Sol', precio='900.00')
    inactivo = crear_producto('Oculto', activo=False)
    gemini.models.generate_content.return_value = respuesta_gemini(
        f'Te recomiendo estas piezas.\nPRODUCTOS_SUGERIDOS: {p1.id},{p2.id},{p1.id},{inactivo.id},9999')

    resultado = services.responder(_historial('Busco un regalo'))

    assert resultado['texto'] == 'Te recomiendo estas piezas.'    # la línea técnica no llega al usuario
    # Sin repetidos, sin productos inactivos ni inexistentes, en el orden sugerido
    assert [p['id'] for p in resultado['productos']] == [p1.id, p2.id]
    primero = resultado['productos'][0]
    assert primero['nombre'] == 'Anillo Luna'
    assert primero['precio'] == '1500.00'
    assert primero['url'] == reverse('productos:detalle', args=[p1.slug])   # URL real, no inventada


def test_tu30b_se_envia_el_modelo_el_historial_y_las_instrucciones(gemini, respuesta_gemini):
    gemini.models.generate_content.return_value = respuesta_gemini('Hola')

    services.responder([{'role': 'user', 'content': 'Hola'},
                        {'role': 'assistant', 'content': '¿En qué te ayudo?'},
                        {'role': 'user', 'content': 'Quiero un anillo'}])

    kwargs = gemini.models.generate_content.call_args.kwargs
    assert kwargs['model'] == django_settings.CHATBOT_MODEL
    assert [c.role for c in kwargs['contents']] == ['user', 'model', 'user']   # assistant -> model
    assert 'Eres el asistente virtual de Bejeweled' in kwargs['config'].system_instruction


def test_tu30c_sin_linea_de_productos_no_hay_tarjetas(gemini, respuesta_gemini):
    gemini.models.generate_content.return_value = respuesta_gemini('Envíos de 3 a 5 días hábiles.')

    resultado = services.responder(_historial('¿Cuánto tarda el envío?'))

    assert resultado == {'texto': 'Envíos de 3 a 5 días hábiles.', 'productos': []}


def test_tu30d_respuesta_vacia_devuelve_mensaje_de_error(gemini, respuesta_gemini):
    gemini.models.generate_content.return_value = respuesta_gemini('   ')

    assert services.responder(_historial()) == {'texto': services.MENSAJE_ERROR, 'productos': []}


def test_tu30e_sin_clave_configurada_no_se_llama_a_gemini(settings):
    settings.CHATBOT_CONFIGURADO = False

    with patch('chatbot.services._obtener_cliente') as obtener:
        resultado = services.responder(_historial())

    assert resultado == {'texto': services.MENSAJE_NO_CONFIGURADO, 'productos': []}
    obtener.assert_not_called()


@pytest.mark.parametrize('texto, esperado', [
    ('Hola\nPRODUCTOS_SUGERIDOS: 1,2,3', ('Hola', [1, 2, 3])),
    ('Hola\nPRODUCTOS_SUGERIDOS: 5,5,6', ('Hola', [5, 6])),               # sin repetidos
    ('Hola\nPRODUCTOS_SUGERIDOS: 1,2,3,4,5,6', ('Hola', [1, 2, 3, 4])),   # máximo 4
    ('Hola\nPRODUCTOS_SUGERIDOS: 1,abc, ,7', ('Hola', [1, 7])),           # ignora basura
    ('Solo texto', ('Solo texto', [])),
])
def test_tu30f_extraccion_de_ids_de_productos(texto, esperado):
    assert services._extraer_ids_productos(texto) == esperado


# ----------------------------------------------------------------- TU-31
@pytest.mark.parametrize('codigo', [429, 503])
def test_tu31_reintenta_un_maximo_de_tres_veces_y_termina(gemini, codigo):
    gemini.models.generate_content.side_effect = genai_errors.APIError(
        codigo, {'error': {'message': 'saturado', 'status': 'UNAVAILABLE'}})

    with patch('chatbot.services.time.sleep') as dormir:
        resultado = services.responder(_historial())

    assert gemini.models.generate_content.call_count == 3          # no hay bucle infinito
    assert [c.args[0] for c in dormir.call_args_list] == [1, 2]    # espera 1 s y luego 2 s
    assert resultado['productos'] == []
    assert 'muchas solicitudes' in resultado['texto']


def test_tu31b_si_un_reintento_funciona_devuelve_la_respuesta(gemini, respuesta_gemini):
    gemini.models.generate_content.side_effect = [
        genai_errors.APIError(429, {'error': {'message': 'cuota'}}),
        respuesta_gemini('Ya estoy aquí'),
    ]

    with patch('chatbot.services.time.sleep') as dormir:
        resultado = services.responder(_historial())

    assert resultado['texto'] == 'Ya estoy aquí'
    assert gemini.models.generate_content.call_count == 2
    dormir.assert_called_once_with(1)


@pytest.mark.parametrize('codigo', [400, 401, 500])
def test_tu31c_otros_errores_no_se_reintentan(gemini, codigo):
    gemini.models.generate_content.side_effect = genai_errors.APIError(
        codigo, {'error': {'message': 'fallo'}})

    with patch('chatbot.services.time.sleep') as dormir:
        resultado = services.responder(_historial())

    assert gemini.models.generate_content.call_count == 1
    dormir.assert_not_called()
    assert resultado == {'texto': services.MENSAJE_ERROR, 'productos': []}


def test_tu31d_un_error_inesperado_nunca_rompe_la_pagina(gemini):
    gemini.models.generate_content.side_effect = RuntimeError('algo raro')

    assert services.responder(_historial()) == {'texto': services.MENSAJE_ERROR, 'productos': []}


# ------------------------------------------------------------------ EXTRAS
@pytest.mark.parametrize('cuerpo', ['{no es json', '{}', '{"mensaje": "   "}'])
def test_ex16_la_vista_rechaza_mensajes_invalidos(client, cuerpo):
    with patch('chatbot.views.responder') as responder:
        respuesta = client.post(reverse('chatbot:enviar_mensaje'), data=cuerpo,
                                content_type='application/json')

    assert respuesta.status_code == 400
    responder.assert_not_called()


def test_ex17_la_vista_guarda_la_conversacion_y_recorta_mensajes_largos(client):
    largo = 'a' * 1500

    with patch('chatbot.views.responder', return_value={'texto': 'Hola', 'productos': []}):
        respuesta = client.post(reverse('chatbot:enviar_mensaje'),
                                data=json.dumps({'mensaje': largo}),
                                content_type='application/json')

    assert respuesta.status_code == 200
    assert respuesta.json() == {'respuesta': 'Hola', 'productos': []}
    mensajes = list(Mensaje.objects.order_by('id'))
    assert [m.rol for m in mensajes] == ['user', 'assistant']
    assert len(mensajes[0].contenido) == 1000
