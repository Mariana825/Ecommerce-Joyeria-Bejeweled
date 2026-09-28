"""
Servicio del chatbot de atención general.

Usa la API de Gemini (Google) para responder dudas generales sobre la
tienda: categorías disponibles, materiales, envíos, devoluciones, cuidado
de las joyas, cómo comprar, etc.

Diseño defensivo: si la API no está configurada o la petición falla, se
regresa un mensaje de error amigable en vez de romper la conversación.
"""

import logging

from django.conf import settings
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from productos.models import Categoria, Coleccion, Material

logger = logging.getLogger(__name__)

MENSAJE_NO_CONFIGURADO = (
    'El asistente todavía no está disponible: falta configurar la clave de '
    'la API de Gemini (GEMINI_API_KEY) en el archivo .env.'
)
MENSAJE_ERROR = (
    'No pude conectarme con el asistente en este momento. Por favor intenta '
    'de nuevo en unos segundos, o contáctanos en hola@bejeweled.com.'
)

INSTRUCCIONES_BASE = """\
Eres el asistente virtual de Bejeweled, una joyería en línea. Respondes en \
español, con un tono cálido, cercano y profesional — como una asesora de \
tienda experta, nunca robótico.

Puedes ayudar con:
- Explicar categorías, materiales y colecciones disponibles (se listan abajo).
- Recomendar qué tipo de pieza conviene según la ocasión, el presupuesto o \
el estilo que describa la persona, en términos generales (sin inventar \
productos o precios específicos que no tengas).
- Explicar cómo comprar: agregar al carrito, iniciar sesión, dirección de \
envío y pago (por ahora solo con PayPal, en modo de pruebas/sandbox).
- Preguntas frecuentes: cuidado de joyas, guía de tallas de anillos, \
política de devoluciones (30 días desde la entrega, la pieza debe estar sin \
uso y con su empaque original), garantía de por vida contra defectos de \
fabricación, y tiempos de envío (nacional 3 a 5 días hábiles).
- Dudas generales sobre materiales: diferencias entre oro 18k, 14k, oro \
blanco, plata 925, acero inoxidable y chapa de oro; cómo limpiarlas y \
conservarlas.

Reglas importantes:
- NO inventes precios, existencias ni nombres de productos que no te hayan \
sido proporcionados. Si te preguntan por un producto específico, invita a \
la persona a buscarlo en el catálogo (/catalogo/) y ofrécele ayuda general \
sobre esa categoría o material mientras tanto.
- NO puedes acceder al carrito, cuenta o pedidos de la persona; si necesita \
ver eso, indícale la sección correspondiente del sitio (Mi cuenta > Mis \
pedidos, por ejemplo).
- Sé breve: 2 a 4 oraciones por respuesta, salvo que te pidan más detalle.
- Si la pregunta no tiene que ver con la joyería, la tienda o el proceso de \
compra, redirige la conversación amablemente hacia cómo puedes ayudar.
"""


def _contexto_catalogo():
    """Arma un resumen del catálogo real para que el asistente no invente datos."""
    categorias = ', '.join(Categoria.objects.filter(activa=True).values_list('nombre', flat=True))
    materiales = ', '.join(Material.objects.values_list('nombre', flat=True))
    colecciones = ', '.join(Coleccion.objects.filter(activa=True).values_list('nombre', flat=True))

    partes = []
    if categorias:
        partes.append(f'Categorías disponibles: {categorias}.')
    if materiales:
        partes.append(f'Materiales que trabajamos: {materiales}.')
    if colecciones:
        partes.append(f'Colecciones actuales: {colecciones}.')

    return '\n'.join(partes)


def _system_prompt(idioma='es'):
    contexto = _contexto_catalogo()
    instrucciones = INSTRUCCIONES_BASE
    if idioma != 'es':
        nombre_idioma = dict(settings.IDIOMAS_DISPONIBLES).get(idioma, idioma)
        instrucciones += (
            f'\n\nIMPORTANTE: responde siempre en {nombre_idioma} (código "{idioma}"), '
            'sin importar en qué idioma escriba la persona, porque así configuró el '
            'sitio. Traduce de forma natural, no literal.'
        )
    if contexto:
        return f'{instrucciones}\n\nInformación actual de la tienda:\n{contexto}'
    return instrucciones


_cliente = None  # se crea una sola vez y se reutiliza entre peticiones


def _obtener_cliente():
    global _cliente
    if _cliente is None:
        _cliente = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _cliente


def _historial_a_contenidos(historial):
    """
    Convierte el historial interno [{"role": "user"|"assistant", "content": str}, ...]
    al formato que espera la API de Gemini: una lista de `types.Content`, con
    el rol "model" en vez de "assistant" (así se llama del lado de Gemini).
    """
    contenidos = []
    for turno in historial:
        rol = 'model' if turno.get('role') == 'assistant' else 'user'
        contenidos.append(
            types.Content(role=rol, parts=[types.Part.from_text(text=turno.get('content', ''))])
        )
    return contenidos


def responder(historial, idioma='es'):
    """
    `historial` es una lista de dicts [{"role": "user"|"assistant", "content": str}, ...]
    con el mensaje más reciente al final. `idioma` es el código elegido por el
    visitante en el selector del header.

    Realiza hasta 3 intentos cuando Gemini devuelve un error temporal (503/429).
    """
    if not settings.CHATBOT_CONFIGURADO:
        return MENSAJE_NO_CONFIGURADO

    try:
        cliente = _obtener_cliente()

        config = types.GenerateContentConfig(
            system_instruction=_system_prompt(idioma),
            max_output_tokens=500,
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.LOW
            ),
        )

        ultimo_error = None

        for intento in range(3):
            try:
                respuesta = cliente.models.generate_content(
                    model=settings.CHATBOT_MODEL,
                    contents=_historial_a_contenidos(historial),
                    config=config,
                )

                texto = (getattr(respuesta, 'text', None) or '').strip()

                if texto:
                    return texto

                return MENSAJE_ERROR

            except genai_errors.APIError as error:
                ultimo_error = error

                # 503 = servicio temporalmente no disponible
                # 429 = demasiadas solicitudes / límite temporal
                if error.code in (429, 503) and intento < 2:
                    espera = 2 ** intento
                    logger.warning(
                        'Gemini devolvió %s. Reintentando en %s segundos '
                        '(intento %s/3).',
                        error.code,
                        espera,
                        intento + 1,
                    )

                    import time
                    time.sleep(espera)
                    continue

                raise

        if ultimo_error:
            raise ultimo_error

        return MENSAJE_ERROR

    except genai_errors.APIError as error:
        logger.error(
            'Error llamando a la API de Gemini: %s',
            error,
        )

        if error.code == 503:
            return (
                'El asistente está recibiendo muchas solicitudes en este '
                'momento. Por favor intenta nuevamente en unos segundos.'
            )

        if error.code == 429:
            return (
                'El asistente está recibiendo muchas solicitudes en este '
                'momento. Por favor espera unos segundos e inténtalo de nuevo.'
            )

        return MENSAJE_ERROR

    except Exception:
        logger.exception('Error inesperado en el chatbot')
        return MENSAJE_ERROR