import threading

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .emails import avisar_nuevo_producto
from .models import Producto



@receiver(post_save, sender=Producto)
def avisar_suscriptores(sender, instance, created, **kwargs):
    if created and instance.activo:
        transaction.on_commit(
            lambda: threading.Thread(
                target=avisar_nuevo_producto, args=(instance.pk,), daemon=True
            ).start()
        )