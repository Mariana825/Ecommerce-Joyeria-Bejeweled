from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from productos.models import Producto

from .models import MovimientoInventario
from .permissions import TieneAPIKey
from .serializers import (
    AjusteStockSerializer, MovimientoInventarioSerializer, ProductoStockSerializer,
)


class ProductoStockListView(generics.ListAPIView):
    """GET /api/inventario/productos/ — stock de todo el catálogo."""

    queryset = Producto.objects.select_related('categoria').order_by('nombre')
    serializer_class = ProductoStockSerializer
    permission_classes = [TieneAPIKey]

    def get_queryset(self):
        queryset = super().get_queryset()
        activo = self.request.query_params.get('activo')
        if activo in ('true', '1'):
            queryset = queryset.filter(activo=True)
        elif activo in ('false', '0'):
            queryset = queryset.filter(activo=False)
        return queryset


class ProductoStockDetailView(generics.RetrieveAPIView):
    """GET /api/inventario/productos/<id>/ — stock de un producto."""

    queryset = Producto.objects.select_related('categoria')
    serializer_class = ProductoStockSerializer
    permission_classes = [TieneAPIKey]


class AjustarStockView(APIView):
    """
    POST /api/inventario/productos/<id>/ajustar/

    Body: {"cantidad": -2, "motivo": "venta", "referencia_pedido": "123"}

    `cantidad` es un delta: negativo para descontar (una venta), positivo
    para sumar (un reabastecimiento o una devolución). El ajuste es atómico
    (usa select_for_update) para que dos ventas simultáneas del mismo
    producto no puedan dejar el stock en negativo ni pisarse entre sí.
    """

    permission_classes = [TieneAPIKey]

    def post(self, request, pk):
        datos = AjusteStockSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        cantidad = datos.validated_data['cantidad']
        motivo = datos.validated_data['motivo']
        referencia_pedido = datos.validated_data['referencia_pedido']

        with transaction.atomic():
            producto = get_object_or_404(
                Producto.objects.select_for_update(), pk=pk
            )

            nuevas_existencias = producto.existencias + cantidad
            if nuevas_existencias < 0:
                return Response(
                    {
                        'error': 'No hay existencias suficientes para esta salida.',
                        'existencias_actuales': producto.existencias,
                        'cantidad_solicitada': cantidad,
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            producto.existencias = nuevas_existencias
            producto.save(update_fields=['existencias', 'actualizado'])

            movimiento = MovimientoInventario.objects.create(
                producto=producto,
                tipo=(MovimientoInventario.Tipo.SALIDA if cantidad < 0
                      else MovimientoInventario.Tipo.ENTRADA),
                cantidad=cantidad,
                existencias_resultantes=nuevas_existencias,
                motivo=motivo,
                referencia_pedido=referencia_pedido,
            )

        return Response(
            {
                'producto_id': producto.id,
                'existencias': producto.existencias,
                'disponible': producto.disponible,
                'movimiento_id': movimiento.id,
            },
            status=status.HTTP_200_OK,
        )


class MovimientosListView(generics.ListAPIView):
    """GET /api/inventario/movimientos/ — bitácora de cambios de stock."""

    queryset = MovimientoInventario.objects.select_related('producto').all()
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [TieneAPIKey]

    def get_queryset(self):
        queryset = super().get_queryset()
        producto_id = self.request.query_params.get('producto')
        if producto_id and producto_id.isdigit():
            queryset = queryset.filter(producto_id=producto_id)
        return queryset[:200]  # tope simple en vez de paginación completa
