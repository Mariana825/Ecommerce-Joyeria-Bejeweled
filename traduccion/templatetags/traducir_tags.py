from django import template

from traduccion.context_processors import idioma_actual
from traduccion.services import traducir_texto

register = template.Library()


@register.filter(name='traducir')
def traducir(texto, request=None):
    """
    Traduce `texto` al idioma elegido por el visitante.

    Uso en plantillas:
        {% load traducir_tags %}
        {{ producto.nombre|traducir:request }}

    Si no se pasa `request` (o no hay uno disponible), regresa el texto
    sin cambios — así el filtro nunca rompe una plantilla.
    """
    if request is None:
        return texto

    idioma = idioma_actual(request)
    return traducir_texto(str(texto), idioma_destino=idioma)
