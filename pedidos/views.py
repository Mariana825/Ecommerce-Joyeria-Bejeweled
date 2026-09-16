from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from carrito.carrito import Carrito
from usuarios.models import DireccionEnvio

from .models import Pedido, PedidoItem


@login_required
def checkout(request):
    carrito = Carrito(request)

    if len(carrito) == 0:
        messages.warning(request, 'Tu carrito está vacío.')
        return redirect('productos:catalogo')

    direcciones = request.user.direcciones.all()

    if request.method == 'POST':
        direccion_id = request.POST.get('direccion_id')
        direccion = get_object_or_404(DireccionEnvio, id=direccion_id, usuario=request.user)

        # Verificamos existencias justo antes de confirmar, por si cambiaron.
        for item in carrito:
            producto = item['producto']
            if item['cantidad'] > producto.existencias:
                messages.error(
                    request,
                    f'Ya no hay suficientes existencias de "{producto.nombre}". '
                    f'Disponibles: {producto.existencias}.'
                )
                return redirect('carrito:ver_carrito')

        with transaction.atomic():
            pedido = Pedido.objects.create(
                usuario=request.user,
                direccion_envio=direccion,
                nombre_destinatario=direccion.destinatario,
                calle=direccion.calle,
                numero=direccion.numero,
                colonia=direccion.colonia,
                ciudad=direccion.ciudad,
                estado_direccion=direccion.estado,
                codigo_postal=direccion.codigo_postal,
                pais=direccion.pais,
                telefono_contacto=direccion.telefono_contacto,
                estado=Pedido.Estado.PENDIENTE_PAGO,
            )

            for item in carrito:
                producto = item['producto']
                PedidoItem.objects.create(
                    pedido=pedido,
                    producto=producto,
                    nombre_producto=producto.nombre,
                    precio_unitario=item['precio'],
                    cantidad=item['cantidad'],
                )
                # Reservamos el inventario al confirmar el pedido.
                producto.existencias -= item['cantidad']
                producto.save(update_fields=['existencias'])

        carrito.vaciar()
        messages.success(request, f'Tu pedido #{pedido.pk} fue registrado.')
        return redirect('pedidos:pago_pendiente', pedido_id=pedido.pk)

    return render(request, 'pedidos/checkout.html', {
        'carrito': carrito,
        'direcciones': direcciones,
    })


@login_required
def pago_pendiente(request, pedido_id):
    """
    Página que confirma que el pedido se registró y queda pendiente de pago.

    NOTA: aquí es donde se integrará la API de PayPal en la siguiente etapa
    del proyecto, para que el usuario complete el pago del pedido.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    return render(request, 'pedidos/pago_pendiente.html', {'pedido': pedido})


@login_required
def detalle_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    return render(request, 'pedidos/detalle_pedido.html', {'pedido': pedido})
