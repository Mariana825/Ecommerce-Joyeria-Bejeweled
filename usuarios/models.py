from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Perfil(models.Model):
    """Datos adicionales del usuario, más allá del User de Django."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil'
    )
    telefono = models.CharField(max_length=20, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatares/', blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'

    def __str__(self):
        return f'Perfil de {self.usuario.username}'


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_o_actualizar_perfil(sender, instance, created, **kwargs):
    """Crea automáticamente un Perfil cuando se crea un nuevo User."""
    if created:
        Perfil.objects.create(usuario=instance)
    else:
        # Si el perfil no existiera por alguna razón (usuarios creados antes
        # de agregar este modelo), lo creamos también aquí.
        Perfil.objects.get_or_create(usuario=instance)


class DireccionEnvio(models.Model):
    """Una dirección de envío guardada por el usuario."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='direcciones'
    )
    etiqueta = models.CharField(
        max_length=50, blank=True,
        help_text="Ej: 'Casa', 'Oficina'"
    )
    destinatario = models.CharField(max_length=150)
    calle = models.CharField(max_length=200)
    numero = models.CharField(max_length=20, blank=True)
    colonia = models.CharField(max_length=120, blank=True)
    ciudad = models.CharField(max_length=100)
    estado = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=20)
    pais = models.CharField(max_length=100, default='México')
    telefono_contacto = models.CharField(max_length=20, blank=True)
    predeterminada = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Dirección de envío'
        verbose_name_plural = 'Direcciones de envío'
        ordering = ['-predeterminada', '-creado']

    def __str__(self):
        return f'{self.destinatario} - {self.ciudad} ({self.usuario.username})'

    def save(self, *args, **kwargs):
        # Si esta dirección se marca como predeterminada, desmarcamos las demás.
        if self.predeterminada:
            DireccionEnvio.objects.filter(
                usuario=self.usuario, predeterminada=True
            ).exclude(pk=self.pk).update(predeterminada=False)
        super().save(*args, **kwargs)
