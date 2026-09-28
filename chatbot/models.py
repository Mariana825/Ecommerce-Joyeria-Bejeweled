from django.conf import settings
from django.db import models


class Conversacion(models.Model):
    """
    Una conversación con el asistente. Se identifica por la clave de sesión
    del navegador, para que funcione tanto con usuarios anónimos como con
    usuarios que iniciaron sesión.
    """

    clave_sesion = models.CharField(max_length=40, db_index=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='conversaciones_chatbot',
    )
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conversación'
        verbose_name_plural = 'Conversaciones'
        ordering = ['-actualizada']

    def __str__(self):
        quien = self.usuario.username if self.usuario else 'Visitante anónimo'
        return f'Conversación #{self.pk} — {quien}'


class Mensaje(models.Model):
    class Rol(models.TextChoices):
        USUARIO = 'user', 'Visitante'
        ASISTENTE = 'assistant', 'Asistente'

    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name='mensajes')
    rol = models.CharField(max_length=10, choices=Rol.choices)
    contenido = models.TextField()
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mensaje'
        verbose_name_plural = 'Mensajes'
        ordering = ['creado']

    def __str__(self):
        return f'{self.get_rol_display()}: {self.contenido[:50]}'
