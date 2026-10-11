from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .email import enviar_correo_compra
from .models import Pedido


@receiver(pre_save, sender=Pedido)
def recordar_estado_anterior(sender, instance, **kwargs):
    if instance.pk:
        instance._estado_anterior = (
            Pedido.objects.filter(pk=instance.pk)
            .values_list('estado', flat=True)
            .first()
        )
    else:
        instance._estado_anterior = None


@receiver(post_save, sender=Pedido)
def correo_al_pagar(sender, instance, created, **kwargs):
    pasa_a_pagado = (
        instance.estado == Pedido.Estado.PAGADO
        and getattr(instance, '_estado_anterior', None) != Pedido.Estado.PAGADO
    )
    if pasa_a_pagado:
        transaction.on_commit(lambda: enviar_correo_compra(instance))