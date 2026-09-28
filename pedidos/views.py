from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from carrito.carrito import Carrito
from inventario import cliente as inventario_cliente
from inventario.cliente import ErrorInventario, StockInsuficiente
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

        # Verificación rápida en base de datos antes de llamar a la API
        # (evita reservar stock por HTTP si de entrada ya sabemos que falta).
        for item in carrito:
            producto = item['producto']
            if item['cantidad'] > producto.existencias:
                messages.error(
                    request,
                    f'Ya no hay suficientes existencias de "{producto.nombre}". '
                    f'Disponibles: {producto.existencias}.'
                )
                return redirect('carrito:ver_carrito')

        # 1) Creamos el pedido y sus artículos en la base de datos. Esta parte
        #    NO toca el inventario todavía — el stock se descuenta después,
        #    a través de la API, una vez que ya existe un pedido al que
        #    referenciar cada movimiento.
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

        # 2) Descontamos el inventario llamando a la API de inventario — una
        #    petición HTTPS por artículo. Si alguna falla (por ejemplo, otra
        #    compra se adelantó y ya no hay existencias), revertimos las que
        #    sí se alcanzaron a descontar y cancelamos el pedido.
        descontados = []  # [(producto_id, cantidad), ...] ya confirmados por la API
        error_inventario = None

        for item in carrito:
            producto = item['producto']
            try:
                inventario_cliente.descontar_stock(
                    producto.id, item['cantidad'], referencia_pedido=str(pedido.id)
                )
                descontados.append((producto.id, item['cantidad']))
            except StockInsuficiente:
                error_inventario = f'Ya no hay existencias suficientes de "{producto.nombre}".'
                break
            except ErrorInventario:
                error_inventario = (
                    'No se pudo actualizar el inventario en este momento. Intenta de nuevo.'
                )
                break

        if error_inventario:
            # Compensación: devolvemos el stock de lo que sí se alcanzó a
            # descontar, en la medida de lo posible (best effort).
            for producto_id, cantidad in descontados:
                try:
                    inventario_cliente.reponer_stock(
                        producto_id, cantidad,
                        motivo='Compensación: pedido cancelado por falta de inventario',
                        referencia_pedido=str(pedido.id),
                    )
                except ErrorInventario:
                    pass  # ya quedó registrado en el log del cliente de la API

            pedido.estado = Pedido.Estado.CANCELADO
            pedido.save(update_fields=['estado', 'actualizado'])

            messages.error(request, error_inventario)
            return redirect('carrito:ver_carrito')

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
    Página donde el comprador completa el pago con PayPal (Sandbox), o ve
    el aviso de que el pago aún no está configurado en el servidor.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    return render(request, 'pedidos/pago_pendiente.html', {
        'pedido': pedido,
        'paypal_configurado': settings.PAYPAL_CONFIGURADO,
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
        'paypal_currency': settings.PAYPAL_CURRENCY,
    })


@login_required
def detalle_pedido(request, pedido_id):
    pedido = get_object_or_404(
        Pedido,
        id=pedido_id,
        usuario=request.user
    )

    return render(request, 'pedidos/detalle_pedido.html', {
        'pedido': pedido,
        'paypal_configurado': settings.PAYPAL_CONFIGURADO,
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
        'paypal_currency': settings.PAYPAL_CURRENCY,
    })