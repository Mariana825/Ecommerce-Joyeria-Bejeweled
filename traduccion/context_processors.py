from django.conf import settings

CLAVE_SESION_IDIOMA = 'idioma'


def idioma_actual(request):
    """Idioma elegido por el visitante en esta sesión (ES por defecto)."""
    return request.session.get(CLAVE_SESION_IDIOMA, settings.IDIOMA_POR_DEFECTO)


def datos_idioma(request):
    """Hace disponible el idioma actual y la lista de idiomas en toda plantilla."""
    return {
        'idioma_actual': idioma_actual(request),
        'idiomas_disponibles': settings.IDIOMAS_DISPONIBLES,
    }
