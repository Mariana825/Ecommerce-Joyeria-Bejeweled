from django.conf import settings
from django.db import models

from productos.models import Producto
from usuarios.models import DireccionEnvio


class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE_PAGO = 'pendiente_pago', 'Pendiente de pago'
        PAGADO = 'pagado', 'Pagado'
        EN_PROCESO = 'en_proceso', 'En proceso'
        ENVIADO = 'enviado', 'Enviado'
        ENTREGADO = 'entregado', 'Entregado'
        CANCELADO = 'cancelado', 'Cancelado'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pedidos'
    )
    direccion_envio = models.ForeignKey(
        DireccionEnvio, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Copia de los datos de envío al momento del pedido (por si la dirección
    # original se edita o elimina después).
    nombre_destinatario = models.CharField(max_length=150)
    calle = models.CharField(max_length=200)
    numero = models.CharField(max_length=20, blank=True)
    colonia = models.CharField(max_length=120, blank=True)
    ciudad = models.CharField(max_length=100)
    estado_direccion = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=20)
    pais = models.CharField(max_length=100)
    telefono_contacto = models.CharField(max_length=20, blank=True)

    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE_PAGO)

    # Método y referencia de pago: se completará al integrar la API de
    # PayPal. Por ahora el pedido se crea y queda pendiente de pago.
    metodo_pago = models.CharField(max_length=50, blank=True, default='')
    referencia_pago = models.CharField(max_length=100, blank=True, default='')

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-creado']

    def __str__(self):
        return f'Pedido #{self.pk} - {self.usuario}'

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())


class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    nombre_producto = models.CharField(max_length=200)  # copia por si el producto cambia/se borra
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Artículo de pedido'
        verbose_name_plural = 'Artículos de pedido'

    def __str__(self):
        return f'{self.cantidad} x {self.nombre_producto}'

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad
