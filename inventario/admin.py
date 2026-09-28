from django.contrib import admin

from .models import MovimientoInventario


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = (
        'creado', 'producto', 'tipo', 'cantidad',
        'existencias_resultantes', 'motivo', 'referencia_pedido',
    )
    list_filter = ('tipo', 'creado')
    search_fields = ('producto__nombre', 'motivo', 'referencia_pedido')
    date_hierarchy = 'creado'

    # La bitácora se llena únicamente a través de la API; no tiene sentido
    # crear o editar movimientos a mano desde el admin.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
