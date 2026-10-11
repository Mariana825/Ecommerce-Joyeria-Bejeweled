"""
Servicio del chatbot de atención general.

Usa la API de Gemini (Google) para responder dudas generales sobre la
tienda y recomendar productos reales del catálogo.

Gemini NO genera imágenes ni URLs de productos.
Cuando recomienda productos, devuelve sus IDs y Django obtiene la
información real directamente de la base de datos.
"""

import logging
import time

from django.conf import settings
from django.urls import reverse
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from productos.models import Categoria, Coleccion, Material, Producto

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
Eres el asistente virtual de Bejeweled, una joyería en línea mexicana.

Tu personalidad:
- Eres cálida, amable y profesional.
- Hablas como una asesora de joyería, no como un robot.
- Respondes en español de México.
- Sé natural y evita comenzar siempre con "Claro".
- No utilices demasiados emojis.
- Sé breve y fácil de leer.

Puedes ayudar con:

PRODUCTOS:
- Recomendar productos concretos del catálogo.
- Buscar productos por categoría.
- Buscar productos por material.
- Buscar productos por colección.
- Recomendar productos según ocasión.
- Recomendar regalos.
- Recomendar productos según estilo.
- Recomendar productos según presupuesto.
- Comparar productos.
- Explicar las características de un producto.
- Indicar si un producto está disponible o agotado.

TIENDA:
- Explicar categorías, materiales y colecciones.
- Explicar cómo comprar.
- Explicar cómo agregar productos al carrito.
- Explicar el proceso de pago.
- Explicar que actualmente el pago se realiza mediante PayPal en modo
  de pruebas/sandbox.
- Explicar envíos nacionales de 3 a 5 días hábiles.
- Explicar devoluciones dentro de los 30 días desde la entrega.
- Explicar que la pieza debe estar sin uso y conservar su empaque original.
- Explicar la garantía de por vida contra defectos de fabricación.
- Explicar el cuidado de las joyas.
- Explicar diferencias entre materiales.

REGLAS SOBRE PRODUCTOS:

1. SOLO puedes recomendar productos que aparezcan en el catálogo
   proporcionado debajo.

2. NUNCA inventes:
   - nombres de productos
   - precios
   - materiales
   - categorías
   - colecciones
   - existencias
   - promociones
   - características que no aparezcan en los datos proporcionados.

3. Si un producto aparece como AGOTADO, no lo presentes como disponible.
   Puedes mencionarlo como agotado y ofrecer alternativas disponibles.

4. Si el usuario especifica un presupuesto, respétalo.

5. Si el usuario pide un material concreto, recomienda únicamente productos
   de ese material.

6. Si el usuario pide una categoría concreta, respeta esa categoría.

7. Si el usuario pide una colección concreta, respeta esa colección.

8. Si el usuario pide recomendaciones pero no proporciona suficiente
   información, puedes hacer UNA pregunta breve para conocer su estilo,
   ocasión o presupuesto.

9. Cuando recomiendes productos concretos, DEBES terminar tu respuesta
   con una línea independiente exactamente con este formato:

PRODUCTOS_SUGERIDOS: id1,id2,id3

Puedes incluir como máximo 4 productos.

Utiliza únicamente los IDs reales proporcionados en el catálogo.

10. Si NO estás recomendando productos concretos, NO escribas
    PRODUCTOS_SUGERIDOS.

11. No muestres al usuario la línea PRODUCTOS_SUGERIDOS como parte de la
    conversación; esa línea será procesada automáticamente por el sistema.

12. Si preguntan por un producto que no aparece en el catálogo, indica que
    no encuentras ese producto actualmente en el catálogo y no inventes
    información.

RESPUESTAS:
- Normalmente responde en 2 a 4 oraciones.
- Si el usuario solicita más detalles, puedes extenderte.
- Cuando compares productos, puedes utilizar una lista breve.
- Prioriza respuestas útiles y naturales.

OTRAS FUNCIONES:
- NO puedes acceder al carrito personal del usuario.
- NO puedes consultar sus pedidos.
- NO puedes consultar su cuenta personal.
- Si necesita consultar un pedido, indícale que vaya a
  "Mi cuenta > Mis pedidos".
- Si necesita realizar una acción que el chatbot no puede hacer,
  explícale dónde puede realizarla dentro del sitio.

Si la pregunta no está relacionada con Bejeweled, las joyas, los productos,
la tienda o el proceso de compra, redirige amablemente la conversación
hacia lo que puedes ayudar.
"""


def _contexto_catalogo():
    """
    Construye el catálogo real de productos que Gemini puede utilizar.

    Solo se envían productos activos para evitar que Gemini recomiende
    productos que ya no aparecen en la tienda.
    """

    productos = (
        Producto.objects
        .filter(activo=True)
        .select_related('categoria', 'material', 'coleccion')
        .order_by('id')
    )

    lineas = []

    for producto in productos:
        categoria = (
            producto.categoria.nombre
            if producto.categoria
            else 'Sin categoría'
        )

        material = (
            producto.material.nombre
            if producto.material
            else 'Sin material'
        )

        coleccion = (
            producto.coleccion.nombre
            if producto.coleccion
            else 'Sin colección'
        )

        estado = (
            'DISPONIBLE'
            if producto.existencias > 0
            else 'AGOTADO'
        )

        linea = (
            f'ID: {producto.id} | '
            f'Nombre: {producto.nombre} | '
            f'Categoría: {categoria} | '
            f'Material: {material} | '
            f'Colección: {coleccion} | '
            f'Precio: ${producto.precio} MXN | '
            f'Existencias: {producto.existencias} | '
            f'Estado: {estado}'
        )

        if producto.descripcion:
            descripcion = producto.descripcion.replace('\n', ' ').strip()

            # Evita enviar descripciones excesivamente largas a Gemini.
            if len(descripcion) > 300:
                descripcion = descripcion[:300] + '...'

            linea += f' | Descripción: {descripcion}'

        if producto.destacado:
            linea += ' | DESTACADO'

        if producto.es_nuevo:
            linea += ' | NUEVO'

        lineas.append(linea)

    if not lineas:
        return 'Actualmente no hay productos activos en el catálogo.'

    return '\n'.join(lineas)


def _contexto_tienda():
    """
    Información general de la tienda.
    """

    categorias = ', '.join(
        Categoria.objects
        .filter(activa=True)
        .values_list('nombre', flat=True)
    )

    materiales = ', '.join(
        Material.objects.values_list('nombre', flat=True)
    )

    colecciones = ', '.join(
        Coleccion.objects
        .filter(activa=True)
        .values_list('nombre', flat=True)
    )

    partes = []

    if categorias:
        partes.append(f'Categorías disponibles: {categorias}.')

    if materiales:
        partes.append(f'Materiales disponibles: {materiales}.')

    if colecciones:
        partes.append(f'Colecciones actuales: {colecciones}.')

    return '\n'.join(partes)


def _system_prompt(idioma='es'):
    """
    Construye el prompt completo que recibe Gemini.
    """

    instrucciones = INSTRUCCIONES_BASE

    contexto_tienda = _contexto_tienda()
    contexto_catalogo = _contexto_catalogo()

    if idioma != 'es':
        nombre_idioma = dict(
            settings.IDIOMAS_DISPONIBLES
        ).get(idioma, idioma)

        instrucciones += (
            f'\n\nIMPORTANTE: responde siempre en {nombre_idioma} '
            f'(código "{idioma}"), sin importar en qué idioma escriba '
            'la persona. Traduce de forma natural, no literal.'
        )

    return (
        f'{instrucciones}\n\n'
        f'INFORMACIÓN GENERAL DE LA TIENDA:\n'
        f'{contexto_tienda or "No hay información adicional."}\n\n'
        f'CATÁLOGO REAL DE PRODUCTOS:\n'
        f'{contexto_catalogo}'
    )


_cliente = None


def _obtener_cliente():
    """
    Crea el cliente de Gemini una sola vez y lo reutiliza.
    """

    global _cliente

    if _cliente is None:
        _cliente = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

    return _cliente


def _historial_a_contenidos(historial):
    """
    Convierte el historial interno al formato de Gemini.
    """

    contenidos = []

    for turno in historial:
        rol = (
            'model'
            if turno.get('role') == 'assistant'
            else 'user'
        )

        contenidos.append(
            types.Content(
                role=rol,
                parts=[
                    types.Part.from_text(
                        text=turno.get('content', '')
                    )
                ],
            )
        )

    return contenidos


def _extraer_ids_productos(texto):
    """
    Extrae la línea:

        PRODUCTOS_SUGERIDOS: 1,4,8

    y devuelve:
        texto_limpio, [1, 4, 8]
    """

    lineas = texto.splitlines()

    ids = []
    linea_productos = None

    for linea in lineas:
        if linea.strip().startswith('PRODUCTOS_SUGERIDOS:'):
            linea_productos = linea.strip()

            contenido = linea_productos.split(
                ':',
                1
            )[1].strip()

            for valor in contenido.split(','):
                valor = valor.strip()

                if valor.isdigit():
                    ids.append(int(valor))

            break

    if linea_productos:
        texto = texto.replace(
            linea_productos,
            ''
        ).strip()

    # Evitar IDs repetidos conservando el orden.
    ids_unicos = list(dict.fromkeys(ids))

    # Máximo 4 productos.
    ids_unicos = ids_unicos[:4]

    return texto, ids_unicos


def _serializar_productos(ids):
    """
    Obtiene los productos reales desde Django y prepara los datos
    que recibirá el frontend del chatbot.
    """

    if not ids:
        return []

    productos = (
        Producto.objects
        .filter(
            id__in=ids,
            activo=True,
        )
        .select_related(
            'categoria',
            'material',
            'coleccion',
        )
    )

    productos_por_id = {
        producto.id: producto
        for producto in productos
    }

    resultado = []

    for producto_id in ids:
        producto = productos_por_id.get(producto_id)

        if not producto:
            continue

        imagen = None

        if producto.imagen_principal:
            imagen = producto.imagen_principal.url

        resultado.append({
            'id': producto.id,
            'nombre': producto.nombre,
            'precio': str(producto.precio),
            'descripcion': producto.descripcion,
            'imagen': imagen,
            'url': reverse(
                'productos:detalle',
                args=[producto.slug]
            ),
            'disponible': producto.disponible,
            'existencias': producto.existencias,
            'categoria': (
                producto.categoria.nombre
                if producto.categoria
                else None
            ),
            'material': (
                producto.material.nombre
                if producto.material
                else None
            ),
            'coleccion': (
                producto.coleccion.nombre
                if producto.coleccion
                else None
            ),
            'calificacion': producto.calificacion_promedio,
            'total_resenas': producto.total_resenas,
            'destacado': producto.destacado,
            'es_nuevo': producto.es_nuevo,
        })

    return resultado


def responder(historial, idioma='es'):
    """
    Responde al usuario mediante Gemini.

    Devuelve:

    {
        "texto": "...",
        "productos": [...]
    }

    En caso de error devuelve igualmente la estructura anterior para que
    el frontend pueda manejar la respuesta de forma uniforme.
    """

    if not settings.CHATBOT_CONFIGURADO:
        return {
            'texto': MENSAJE_NO_CONFIGURADO,
            'productos': [],
        }

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

                texto = (
                    getattr(respuesta, 'text', None)
                    or ''
                ).strip()

                if not texto:
                    return {
                        'texto': MENSAJE_ERROR,
                        'productos': [],
                    }

                texto_limpio, ids_productos = _extraer_ids_productos(
                    texto
                )

                productos = _serializar_productos(
                    ids_productos
                )

                return {
                    'texto': texto_limpio,
                    'productos': productos,
                }

            except genai_errors.APIError as error:
                ultimo_error = error

                if error.code in (429, 503) and intento < 2:
                    espera = 2 ** intento

                    logger.warning(
                        'Gemini devolvió %s. Reintentando en %s segundos '
                        '(intento %s/3).',
                        error.code,
                        espera,
                        intento + 1,
                    )

                    time.sleep(espera)
                    continue

                raise

        if ultimo_error:
            raise ultimo_error

        return {
            'texto': MENSAJE_ERROR,
            'productos': [],
        }

    except genai_errors.APIError as error:
        logger.error(
            'Error llamando a la API de Gemini: %s',
            error,
        )

        if error.code == 503:
            mensaje = (
                'El asistente está recibiendo muchas solicitudes en este '
                'momento. Por favor intenta nuevamente en unos segundos.'
            )

            return {
                'texto': mensaje,
                'productos': [],
            }

        if error.code == 429:
            mensaje = (
                'El asistente está recibiendo muchas solicitudes en este '
                'momento. Por favor espera unos segundos e inténtalo de nuevo.'
            )

            return {
                'texto': mensaje,
                'productos': [],
            }

        return {
            'texto': MENSAJE_ERROR,
            'productos': [],
        }

    except Exception:
        logger.exception(
            'Error inesperado en el chatbot'
        )

        return {
            'texto': MENSAJE_ERROR,
            'productos': [],
        }