from .carrito import Carrito


def datos_carrito(request):
    """Hace disponible el carrito (y su contador) en todas las plantillas."""
    return {'carrito_actual': Carrito(request)}
