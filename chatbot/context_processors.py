from django.conf import settings


def datos_chatbot(request):
    """Hace disponible si el chatbot está configurado en toda plantilla."""
    return {'chatbot_configurado': settings.CHATBOT_CONFIGURADO}
