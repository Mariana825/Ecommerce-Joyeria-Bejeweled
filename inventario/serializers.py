from rest_framework import serializers

from productos.models import Producto

from .models import MovimientoInventario


class ProductoStockSerializer(serializers.ModelSerializer):
    categoria = serializers.CharField(source='categoria.nombre', default=None, read_only=True)
    disponible = serializers.BooleanField(read_only=True)

    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'slug', 'categoria',
            'existencias', 'disponible', 'activo', 'actualizado',
        ]
        read_only_fields = fields


class MovimientoInventarioSerializer(serializers.ModelSerializer):
    producto = serializers.CharField(source='producto.nombre', read_only=True)
    producto_id = serializers.IntegerField(source='producto.id', read_only=True)

    class Meta:
        model = MovimientoInventario
        fields = [
            'id', 'producto_id', 'producto', 'tipo', 'cantidad',
            'existencias_resultantes', 'motivo', 'referencia_pedido', 'creado',
        ]
        read_only_fields = fields


class AjusteStockSerializer(serializers.Serializer):
    """Cuerpo esperado por POST /api/inventario/productos/<id>/ajustar/."""

    cantidad = serializers.IntegerField(
        help_text='Positivo para sumar existencias, negativo para descontarlas. No puede ser 0.'
    )
    motivo = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    referencia_pedido = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')

    def validate_cantidad(self, valor):
        if valor == 0:
            raise serializers.ValidationError('La cantidad no puede ser 0.')
        return valor
