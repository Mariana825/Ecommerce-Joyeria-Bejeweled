import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def enviar_correo_compra(pedido):
    """Envía la confirmación del pedido al correo del usuario.
    Nunca lanza excepción: si Gmail falla, la compra sigue válida."""
    usuario = pedido.usuario
    if usuario is None or not usuario.email:
        return False

    contexto = {
        'pedido': pedido,
        'usuario': usuario,
        'items': pedido.items.all(),
        'total': pedido.total,
    }
    asunto = f'Bejeweled - Pago confirmado'
    texto = render_to_string('pedidos/email_confirmacion.txt', contexto)
    html = render_to_string('pedidos/email_confirmacion.html', contexto)

    mensaje = EmailMultiAlternatives(
        asunto, texto, settings.DEFAULT_FROM_EMAIL, [usuario.email]
    )
    mensaje.attach_alternative(html, 'text/html')

    try:
        mensaje.send()
        return True
    except Exception:
        logger.exception('No se pudo enviar el correo del pedido %s', pedido.pk)
        return False