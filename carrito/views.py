from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from productos.models import Producto

from .carrito import Carrito


def ver_carrito(request):
    carrito = Carrito(request)
    return render(request, 'carrito/ver_carrito.html', {'carrito': carrito})


@require_POST
def agregar(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id, activo=True)

    if not producto.disponible:
        messages.error(request, 'Ese producto no tiene existencias disponibles.')
        return redirect('productos:detalle', slug=producto.slug)

    try:
        cantidad = int(request.POST.get('cantidad', 1))
    except (TypeError, ValueError):
        cantidad = 1
    cantidad = max(1, cantidad)

    carrito.agregar(producto=producto, cantidad=cantidad)
    messages.success(request, f'"{producto.nombre}" se agregó al carrito.')
    return redirect('carrito:ver_carrito')


@require_POST
def actualizar(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)

    try:
        cantidad = int(request.POST.get('cantidad', 1))
    except (TypeError, ValueError):
        cantidad = 1

    carrito.agregar(producto=producto, cantidad=cantidad, reemplazar_cantidad=True)
    return redirect('carrito:ver_carrito')


@require_POST
def eliminar(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    carrito.eliminar(producto)
    messages.info(request, f'"{producto.nombre}" se eliminó del carrito.')
    return redirect('carrito:ver_carrito')
