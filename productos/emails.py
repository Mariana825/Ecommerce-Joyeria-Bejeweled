import logging

from django.conf import settings
from django.core import mail, signing
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Producto, Suscriptor

logger = logging.getLogger(__name__)

SAL_BAJA = 'newsletter-baja'


def avisar_nuevo_producto(producto_id):
    try:
        producto = Producto.objects.get(pk=producto_id)
        mensajes = []
        for suscriptor in Suscriptor.objects.filter(activo=True):
            token = signing.dumps(suscriptor.email, salt=SAL_BAJA)
            contexto = {
                'producto': producto,
                'url_catalogo': settings.SITE_URL + reverse('productos:catalogo'),
                'url_baja': settings.SITE_URL + reverse(
                    'productos:newsletter_baja', args=[token]
                ),
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
            mensajes.append(mensaje)

        if mensajes:
            mail.get_connection().send_messages(mensajes)
    except Exception:
        logger.exception('No se pudo avisar del producto %s', producto_id)