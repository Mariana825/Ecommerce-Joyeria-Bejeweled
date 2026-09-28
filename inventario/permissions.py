from django.conf import settings
from rest_framework.permissions import BasePermission

ENCABEZADO_API_KEY = 'X-API-Key'


class TieneAPIKey(BasePermission):
    """
    Permiso simple por clave compartida: la petición debe traer el encabezado
    'X-API-Key' con el valor de settings.INVENTARIO_API_KEY.

    Se usa API key en vez de autenticación de usuario porque quien consume
    esta API es la propia aplicación (o, en el futuro, otro sistema/servicio),
    no una persona con sesión iniciada.
    """

    message = 'Falta o es inválida la clave de la API (encabezado X-API-Key).'

    def has_permission(self, request, view):
        if not settings.INVENTARIO_API_KEY:
            # Si no se configuró ninguna clave, la API queda cerrada por
            # completo en vez de abierta por accidente.
            return False
        return request.headers.get(ENCABEZADO_API_KEY) == settings.INVENTARIO_API_KEY
