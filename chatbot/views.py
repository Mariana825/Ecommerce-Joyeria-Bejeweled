import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import Conversacion, Mensaje
from .services import responder
from traduccion.context_processors import idioma_actual

LIMITE_MENSAJE = 1000  # caracteres, para evitar abusos desde el navegador


def _conversacion_de_la_sesion(request):
    if not request.session.session_key:
        request.session.save()  # necesitamos una clave de sesión ya asignada

    clave = request.session.session_key
    conversacion, _ = Conversacion.objects.get_or_create(
        clave_sesion=clave,
        defaults={'usuario': request.user if request.user.is_authenticated else None},
    )
    return conversacion


@require_GET
def historial(request):
    """Historial de la conversación actual, para restaurar el widget al recargar la página."""
    conversacion = _conversacion_de_la_sesion(request)
    mensajes = conversacion.mensajes.values('rol', 'contenido', 'creado')
    return JsonResponse({
        'mensajes': [
            {'rol': m['rol'], 'contenido': m['contenido']} for m in mensajes
        ]
    })


@require_POST
def enviar_mensaje(request):
    try:
        datos = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)

    texto = (datos.get('mensaje') or '').strip()
    if not texto:
        return JsonResponse({'error': 'Escribe un mensaje.'}, status=400)
    if len(texto) > LIMITE_MENSAJE:
        texto = texto[:LIMITE_MENSAJE]

    conversacion = _conversacion_de_la_sesion(request)
    Mensaje.objects.create(conversacion=conversacion, rol=Mensaje.Rol.USUARIO, contenido=texto)

    # Reenviamos como contexto solo los últimos N mensajes (ver settings),
    # para no dejar crecer el costo de cada llamada sin límite.
    recientes = list(
        conversacion.mensajes.order_by('-creado')[:settings.CHATBOT_HISTORIAL_MAXIMO]
    )[::-1]

    # La API de Gemini exige que el primer mensaje sea de rol "user": si el
    # recorte anterior dejó el historial empezando en "assistant", quitamos
    # ese primer mensaje suelto para no romper la alternancia user/assistant.
    if recientes and recientes[0].rol != Mensaje.Rol.USUARIO:
        recientes = recientes[1:]

    historial_api = [{'role': m.rol, 'content': m.contenido} for m in recientes]

    texto_respuesta = responder(historial_api, idioma=idioma_actual(request))

    Mensaje.objects.create(
        conversacion=conversacion, rol=Mensaje.Rol.ASISTENTE, contenido=texto_respuesta
    )

    return JsonResponse({'respuesta': texto_respuesta})
