from django.contrib import admin

from .models import Pedido, PedidoItem


class PedidoItemInline(admin.TabularInline):
    model = PedidoItem
    extra = 0
    readonly_fields = ('producto', 'nombre_producto', 'precio_unitario', 'cantidad')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'estado', 'total', 'creado')
    list_filter = ('estado', 'creado')
    search_fields = ('usuario__username', 'usuario__email', 'nombre_destinatario')
    list_editable = ('estado',)
    inlines = [PedidoItemInline]
    readonly_fields = (
        'usuario', 'nombre_destinatario', 'calle', 'numero', 'colonia',
        'ciudad', 'estado_direccion', 'codigo_postal', 'pais', 'telefono_contacto',
        'creado', 'actualizado',
    )
