"""Traducción Argos: TU-32 y TU-33 (+ extra EX-18). Argos se simula siempre: no hace falta instalarlo."""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from django.test import RequestFactory
from django.urls import reverse

from traduccion import services
from traduccion.services import traducir_texto, traducir_varios


def _traduccion_falsa(resultado='Gold ring'):
    falsa = MagicMock()
    falsa.translate.return_value = resultado
    return falsa


# ----------------------------------------------------------------- TU-32
def test_tu32_traduce_un_texto_valido_y_lo_guarda_en_cache():
    falsa = _traduccion_falsa('Gold ring')

    with patch('traduccion.services._obtener_traduccion', return_value=falsa) as obtener:
        assert traducir_texto('Anillo de oro', 'en') == 'Gold ring'
        assert traducir_texto('Anillo de oro', 'en') == 'Gold ring'   # segunda vez: desde caché

    falsa.translate.assert_called_once_with('Anillo de oro')
    obtener.assert_called_once_with('es', 'en')


def test_tu32b_recorta_espacios_antes_de_traducir():
    falsa = _traduccion_falsa('Gold ring')

    with patch('traduccion.services._obtener_traduccion', return_value=falsa):
        assert traducir_texto('   Anillo de oro  ', 'en') == 'Gold ring'

    falsa.translate.assert_called_once_with('Anillo de oro')


@pytest.mark.parametrize('texto', ['', '   ', None])
def test_tu32c_textos_vacios_regresan_vacio_sin_traducir(texto):
    with patch('traduccion.services._obtener_traduccion') as obtener:
        assert traducir_texto(texto, 'en') == ''
    obtener.assert_not_called()


def test_tu32d_si_el_idioma_destino_es_el_origen_no_se_traduce():
    with patch('traduccion.services._obtener_traduccion') as obtener:
        assert traducir_texto('Anillo de oro', 'es') == 'Anillo de oro'
    obtener.assert_not_called()


def test_tu32e_traducir_varios_traduce_cada_texto():
    falsa = MagicMock()
    falsa.translate.side_effect = lambda texto: texto.upper()

    with patch('traduccion.services._obtener_traduccion', return_value=falsa):
        assert traducir_varios(['anillo', 'collar'], 'en') == ['ANILLO', 'COLLAR']
        assert traducir_varios([' anillo '], 'es') == ['anillo']


# ----------------------------------------------------------------- TU-33
def test_tu33_sin_traduccion_disponible_devuelve_el_texto_original():
    with patch('traduccion.services._obtener_traduccion', return_value=None):
        assert traducir_texto('Anillo de oro', 'en') == 'Anillo de oro'

    assert cache.get(services._clave_cache('Anillo de oro', 'en')) is None   # el fallo no se cachea


def test_tu33b_si_el_modelo_falla_al_traducir_devuelve_el_original():
    rota = MagicMock()
    rota.translate.side_effect = RuntimeError('modelo corrupto')

    with patch('traduccion.services._obtener_traduccion', return_value=rota):
        assert traducir_texto('Anillo de oro', 'en') == 'Anillo de oro'

    assert cache.get(services._clave_cache('Anillo de oro', 'en')) is None


def test_tu33c_paquete_argostranslate_no_instalado(monkeypatch, caplog):
    # `None` en sys.modules hace que "import argostranslate" lance ImportError.
    monkeypatch.setitem(sys.modules, 'argostranslate', None)
    monkeypatch.setitem(sys.modules, 'argostranslate.translate', None)

    assert services._obtener_traduccion('es', 'en') is None
    assert 'argostranslate' in caplog.text
    assert traducir_texto('Anillo de oro', 'en') == 'Anillo de oro'


def test_tu33d_falta_el_modelo_del_par_de_idiomas(monkeypatch, caplog):
    falso = types.ModuleType('argostranslate')
    falso.translate = types.SimpleNamespace(get_installed_languages=lambda: [])   # sin modelos
    monkeypatch.setitem(sys.modules, 'argostranslate', falso)
    monkeypatch.setitem(sys.modules, 'argostranslate.translate', falso.translate)

    assert services._obtener_traduccion('es', 'en') is None
    assert 'Falta el modelo de traducción' in caplog.text
    # El par ya se intentó: no se vuelve a intentar (ni a llenar el log) en cada petición
    assert ('es', 'en') in services._PARES_YA_INTENTADOS


def test_tu33e_con_el_modelo_instalado_se_carga_una_sola_vez(monkeypatch):
    modelo = _traduccion_falsa('Gold ring')
    espanol = types.SimpleNamespace(code='es', get_translation=MagicMock(return_value=modelo))
    ingles = types.SimpleNamespace(code='en')
    falso = types.ModuleType('argostranslate')
    falso.translate = types.SimpleNamespace(get_installed_languages=lambda: [espanol, ingles])
    monkeypatch.setitem(sys.modules, 'argostranslate', falso)
    monkeypatch.setitem(sys.modules, 'argostranslate.translate', falso.translate)

    assert services._obtener_traduccion('es', 'en') is modelo
    assert services._obtener_traduccion('es', 'en') is modelo
    espanol.get_translation.assert_called_once_with(ingles)


# ------------------------------------------------------------------ EXTRAS
@pytest.mark.django_db
def test_ex18_cambiar_idioma_guarda_solo_idiomas_validos(client):
    url = reverse('traduccion:cambiar_idioma')

    client.post(url, {'idioma': 'en'})
    assert client.session['idioma'] == 'en'

    client.post(url, {'idioma': 'klingon'})
    assert client.session['idioma'] == 'en'    # un código inválido no cambia nada
