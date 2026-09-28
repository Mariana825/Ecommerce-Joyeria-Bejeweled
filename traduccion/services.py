"""
Servicio de traducción automática.

Usa el paquete "argostranslate" (https://github.com/argosopentech/argos-translate):
una librería de traducción neuronal de código abierto que corre 100% en
este servidor. No llama a ninguna API externa ni necesita clave — solo hay
que instalar los modelos de idioma una vez (ver el management command
`instalar_modelos_traduccion`) y, a partir de ahí, cada texto se traduce
localmente, sin conexión a internet.

Diseño defensivo: si los modelos todavía no están instalados, o si algo
falla al traducir, se regresa el texto original en vez de romper la
página. Así la tienda sigue funcionando aunque la traducción no esté lista.

Cada texto traducido se guarda en la caché de Django (ver
settings.TRADUCCION_CACHE_SEGUNDOS) para no volver a pasarlo por el modelo
neuronal en cada visita — aunque la traducción sea local, sí consume CPU.
"""

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Objetos `Translation` de argostranslate ya cargados, por par de idiomas
# (origen, destino). Cargar un modelo tiene costo, así que se hace una sola
# vez por proceso y se reutiliza en cada petición.
_TRADUCCIONES_CARGADAS = {}
_PARES_YA_INTENTADOS = set()


def _clave_cache(texto, idioma_destino):
    """Clave corta y estable para la caché, sin importar el largo del texto."""
    huella = hashlib.sha1(texto.encode('utf-8')).hexdigest()
    return f'traduccion:{idioma_destino}:{huella}'


def _obtener_traduccion(idioma_origen, idioma_destino):
    """
    Regresa el objeto `Translation` de argostranslate para este par de
    idiomas, o `None` si el paquete no está instalado o falta el modelo
    correspondiente (en cuyo caso ya se registró un aviso en el log).
    """
    par = (idioma_origen, idioma_destino)
    if par in _TRADUCCIONES_CARGADAS:
        return _TRADUCCIONES_CARGADAS[par]
    if par in _PARES_YA_INTENTADOS:
        # Ya avisamos antes que falta el modelo; no repetir el intento en
        # cada request.
        return None
    _PARES_YA_INTENTADOS.add(par)

    try:
        import argostranslate.translate as at_translate
    except ImportError:
        logger.warning(
            'El paquete "argostranslate" no está instalado. Instala las '
            'dependencias con `pip install -r requirements.txt`.'
        )
        return None

    try:
        idiomas = at_translate.get_installed_languages()
        lang_origen = next((idioma for idioma in idiomas if idioma.code == idioma_origen), None)
        lang_destino = next((idioma for idioma in idiomas if idioma.code == idioma_destino), None)
        traduccion = lang_origen.get_translation(lang_destino) if lang_origen and lang_destino else None
    except Exception:  # noqa: BLE001 — nunca queremos romper la página por esto
        logger.exception('No se pudo cargar el modelo de traducción %s→%s', idioma_origen, idioma_destino)
        return None

    if traduccion is None:
        logger.warning(
            'Falta el modelo de traducción %s→%s. Instálalo con '
            '`python manage.py instalar_modelos_traduccion`.',
            idioma_origen, idioma_destino,
        )
        return None

    _TRADUCCIONES_CARGADAS[par] = traduccion
    return traduccion


def traducir_texto(texto, idioma_destino, idioma_origen='es'):
    """
    Traduce `texto` a `idioma_destino`. Si algo falla, o si el modelo no
    está instalado, regresa el texto original sin lanzar ninguna excepción.
    """
    texto = (texto or '').strip()

    if not texto or idioma_destino == idioma_origen:
        return texto

    clave = _clave_cache(texto, idioma_destino)
    en_cache = cache.get(clave)
    if en_cache is not None:
        return en_cache

    traduccion = _obtener_traduccion(idioma_origen, idioma_destino)
    if traduccion is None:
        return texto

    try:
        traducido = traduccion.translate(texto)
    except Exception:  # noqa: BLE001
        logger.exception('No se pudo traducir el texto con argostranslate')
        return texto

    cache.set(clave, traducido, settings.TRADUCCION_CACHE_SEGUNDOS)
    return traducido


def traducir_varios(textos, idioma_destino, idioma_origen='es'):
    """
    Traduce una lista de textos. A diferencia de una API remota, el modelo
    local no gana nada agrupando varias peticiones en una sola llamada, así
    que simplemente se traduce cada texto (y cada uno respeta su propia
    entrada en caché, igual que `traducir_texto`).
    """
    textos = [(t or '').strip() for t in textos]

    if idioma_destino == idioma_origen:
        return textos

    return [traducir_texto(texto, idioma_destino, idioma_origen) for texto in textos]
