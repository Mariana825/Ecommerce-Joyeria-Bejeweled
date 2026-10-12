import logging
from email.mime.image import MIMEImage

from django.conf import settings
from django.core import mail, signing
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Producto, Suscriptor

logger = logging.getLogger(__name__)

SAL_BAJA = 'newsletter-baja'


def _leer_imagen(producto):
    """Devuelve los bytes de la imagen principal, o None si no hay."""
    campo = getattr(producto, 'imagen_principal', None) or getattr(producto, 'imagen', None)
    if not campo:
        return None
    try:
        with campo.open('rb') as f:
            return f.read()
    except Exception:
        logger.exception('No se pudo leer la imagen del producto %s', producto.pk)
        return None


def avisar_nuevo_producto(producto_id):
    try:
        producto = Producto.objects.get(pk=producto_id)
        url_producto = settings.SITE_URL + reverse('productos:detalle', args=[producto.slug])
        imagen_bytes = _leer_imagen(producto)

        mensajes = []
        for suscriptor in Suscriptor.objects.filter(activo=True):
            token = signing.dumps(suscriptor.email, salt=SAL_BAJA)
            contexto = {
                'producto': producto,
                'url_producto': url_producto,
                'url_baja': settings.SITE_URL + reverse(
                    'productos:newsletter_baja', args=[token]
                ),
                'tiene_imagen': bool(imagen_bytes),
            }
            texto = render_to_string('productos/email_nuevo_producto.txt', contexto)
            html = render_to_string('productos/email_nuevo_producto.html', contexto)

            mensaje = EmailMultiAlternatives(
                f'Nuevo en Bejeweled: {producto.nombre}',
                texto,
                settings.DEFAULT_FROM_EMAIL,
                [suscriptor.email],
            )
            mensaje.attach_alternative(html, 'text/html')

            if imagen_bytes:
                img = MIMEImage(imagen_bytes)
                img.add_header('Content-ID', '<producto_img>')
                img.add_header('Content-Disposition', 'inline', filename='producto.jpg')
                mensaje.mixed_subtype = 'related'
                mensaje.attach(img)

            mensajes.append(mensaje)

        if mensajes:
            mail.get_connection().send_messages(mensajes)
    except Exception:
        logger.exception('No se pudo avisar del producto %s', producto_id)