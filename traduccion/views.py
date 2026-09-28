from django.conf import settings
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .context_processors import CLAVE_SESION_IDIOMA


@require_POST
def cambiar_idioma(request):
    """Guarda el idioma elegido en la sesión y regresa a la misma página."""
    idioma = request.POST.get('idioma', settings.IDIOMA_POR_DEFECTO)
    codigos_validos = {codigo for codigo, _ in settings.IDIOMAS_DISPONIBLES}

    if idioma in codigos_validos:
        request.session[CLAVE_SESION_IDIOMA] = idioma

    return redirect(request.POST.get('siguiente') or 'productos:inicio')
