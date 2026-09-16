from django.contrib import admin

from .models import (
    Categoria, Coleccion, Favorito, ImagenProducto,
    Material, Producto, Resena, Suscriptor,
)


class ImagenProductoInline(admin.TabularInline):
    model = ImagenProducto
    extra = 1


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activa')
    list_filter = ('activa',)
    search_fields = ('nombre',)
    prepopulated_fields = {'slug': ('nombre',)}


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)


@admin.register(Coleccion)
class ColeccionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden', 'activa')
    list_editable = ('orden', 'activa')
    search_fields = ('nombre',)
    prepopulated_fields = {'slug': ('nombre',)}


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        'nombre', 'categoria', 'material', 'coleccion', 'precio',
        'existencias', 'activo', 'destacado', 'es_nuevo',
    )
    list_editable = ('precio', 'existencias', 'activo', 'destacado', 'es_nuevo')
    list_filter = ('categoria', 'material', 'coleccion', 'activo', 'destacado', 'es_nuevo')
    search_fields = ('nombre', 'descripcion')
    prepopulated_fields = {'slug': ('nombre',)}
    inlines = [ImagenProductoInline]
    fieldsets = (
        (None, {
            'fields': ('nombre', 'slug', 'categoria', 'material', 'coleccion', 'descripcion')
        }),
        ('Precio e inventario', {
            'fields': ('precio', 'existencias')
        }),
        ('Imagen y estado', {
            'fields': ('imagen_principal', 'activo', 'destacado', 'es_nuevo')
        }),
    )


@admin.register(Resena)
class ResenaAdmin(admin.ModelAdmin):
    list_display = ('producto', 'usuario', 'calificacion', 'aprobada', 'creada')
    list_filter = ('calificacion', 'aprobada', 'creada')
    list_editable = ('aprobada',)
    search_fields = ('producto__nombre', 'usuario__username', 'comentario')


@admin.register(Favorito)
class FavoritoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'producto', 'creado')
    search_fields = ('usuario__username', 'producto__nombre')


@admin.register(Suscriptor)
class SuscriptorAdmin(admin.ModelAdmin):
    list_display = ('email', 'activo', 'creado')
    list_filter = ('activo',)
    search_fields = ('email',)
