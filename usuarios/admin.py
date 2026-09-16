from django.contrib import admin

from .models import DireccionEnvio, Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'telefono', 'creado')
    search_fields = ('usuario__username', 'usuario__email', 'telefono')


@admin.register(DireccionEnvio)
class DireccionEnvioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'destinatario', 'ciudad', 'estado', 'predeterminada')
    list_filter = ('estado', 'pais', 'predeterminada')
    search_fields = ('usuario__username', 'destinatario', 'ciudad')
