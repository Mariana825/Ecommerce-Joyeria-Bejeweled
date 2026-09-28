from django.db import models

from productos.models import Producto


class MovimientoInventario(models.Model):
    """
    Bitácora de cada cambio de existencias hecho a través de la API.

    Se guarda tanto para poder auditar el inventario (quién/qué motivo bajó
    o subió el stock) como para depurar: cada ajuste queda registrado con el
    saldo resultante, así que siempre se puede reconstruir el historial de
    un producto.
    """

    class Tipo(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada (reabastecimiento)'
        SALIDA = 'salida', 'Salida (venta)'
        AJUSTE = 'ajuste', 'Ajuste manual'

    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name='movimientos_inventario'
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    cantidad = models.IntegerField(
        help_text='Positivo para entradas, negativo para salidas.'
    )
    existencias_resultantes = models.PositiveIntegerField()
    motivo = models.CharField(max_length=200, blank=True)
    referencia_pedido = models.CharField(
        max_length=50, blank=True,
        help_text='ID del pedido que originó el movimiento, si aplica.'
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Movimiento de inventario'
        verbose_name_plural = 'Movimientos de inventario'
        ordering = ['-creado']

    def __str__(self):
        signo = '+' if self.cantidad >= 0 else ''
        return f'{self.producto.nombre}: {signo}{self.cantidad} ({self.get_tipo_display()})'
