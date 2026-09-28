from django.contrib import admin

from .models import Conversacion, Mensaje


class MensajeInline(admin.TabularInline):
    model = Mensaje
    extra = 0
    readonly_fields = ('rol', 'contenido', 'creado')
    can_delete = False


@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'creada', 'actualizada', 'total_mensajes')
    list_filter = ('creada',)
    search_fields = ('usuario__username', 'clave_sesion')
    inlines = [MensajeInline]

    def total_mensajes(self, obj):
        return obj.mensajes.count()
    total_mensajes.short_description = 'Mensajes'
