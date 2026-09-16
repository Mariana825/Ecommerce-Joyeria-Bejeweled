from decimal import Decimal

from django.conf import settings

from productos.models import Producto

CLAVE_SESION_CARRITO = 'carrito'


class Carrito:
    """
    Carrito de compras basado en la sesión del usuario.

    Estructura almacenada en request.session['carrito']:
        {
            "<producto_id>": {"cantidad": int, "precio": "12.50"},
            ...
        }

    Se usa la sesión (en vez de un modelo en base de datos) para que el
    carrito funcione tanto para usuarios anónimos como autenticados sin
    pasos adicionales; esto es un patrón estándar en Django.
    """

    def __init__(self, request):
        self.session = request.session
        carrito = self.session.get(CLAVE_SESION_CARRITO)
        if carrito is None:
            carrito = self.session[CLAVE_SESION_CARRITO] = {}
        self.carrito = carrito

    def agregar(self, producto, cantidad=1, reemplazar_cantidad=False):
        producto_id = str(producto.id)
        if producto_id not in self.carrito:
            self.carrito[producto_id] = {
                'cantidad': 0,
                'precio': str(producto.precio),
            }
        if reemplazar_cantidad:
            self.carrito[producto_id]['cantidad'] = cantidad
        else:
            self.carrito[producto_id]['cantidad'] += cantidad

        # No exceder las existencias disponibles
        if self.carrito[producto_id]['cantidad'] > producto.existencias:
            self.carrito[producto_id]['cantidad'] = producto.existencias
        if self.carrito[producto_id]['cantidad'] < 1:
            self.eliminar(producto)
        else:
            self.guardar()

    def guardar(self):
        self.session.modified = True

    def eliminar(self, producto):
        producto_id = str(producto.id)
        if producto_id in self.carrito:
            del self.carrito[producto_id]
            self.guardar()

    def vaciar(self):
        self.session[CLAVE_SESION_CARRITO] = {}
        self.guardar()

    def __iter__(self):
        producto_ids = self.carrito.keys()
        productos = Producto.objects.filter(id__in=producto_ids)
        mapa_productos = {str(p.id): p for p in productos}

        for producto_id, datos in self.carrito.items():
            producto = mapa_productos.get(producto_id)
            if not producto:
                continue
            item = datos.copy()
            item['producto'] = producto
            item['precio'] = Decimal(item['precio'])
            item['subtotal'] = item['precio'] * item['cantidad']
            yield item

    def __len__(self):
        return sum(item['cantidad'] for item in self.carrito.values())

    def total(self):
        return sum(
            Decimal(item['precio']) * item['cantidad']
            for item in self.carrito.values()
        )
