from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.urls import reverse
from django.utils.text import slugify


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(
        upload_to='categorias/', blank=True, null=True,
        help_text='Imagen de portada que se muestra en la sección de categorías.'
    )
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)


class Material(models.Model):
    """Ej: Oro 18k, Plata 925, Acero inoxidable."""
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Coleccion(models.Model):
    """Colección curada de joyas (ej: Colección Dorada, Elegancia en Plata)."""

    nombre = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to='colecciones/', blank=True, null=True)
    color_acento = models.CharField(
        max_length=7, default='#C9A84C',
        help_text='Color hexadecimal de la franja superior de la tarjeta (ej: #C9A84C).'
    )
    activa = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Colección'
        verbose_name_plural = 'Colecciones'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('productos:coleccion', args=[self.slug])


class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, related_name='productos'
    )
    material = models.ForeignKey(
        Material, on_delete=models.SET_NULL, null=True, blank=True, related_name='productos'
    )
    coleccion = models.ForeignKey(
        Coleccion, on_delete=models.SET_NULL, null=True, blank=True, related_name='productos'
    )
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    existencias = models.PositiveIntegerField(default=0)
    imagen_principal = models.ImageField(upload_to='productos/', blank=True, null=True)
    activo = models.BooleanField(default=True, help_text='Si está desactivado, no se muestra en la tienda.')
    destacado = models.BooleanField(default=False)
    es_nuevo = models.BooleanField(default=False, help_text='Muestra la etiqueta "Nuevo" en el catálogo.')
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['-creado']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nombre)
            slug = base_slug
            contador = 1
            while Producto.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                contador += 1
                slug = f'{base_slug}-{contador}'
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('productos:detalle', args=[self.slug])

    @property
    def disponible(self):
        return self.activo and self.existencias > 0

    @property
    def calificacion_promedio(self):
        """Promedio de estrellas de las reseñas aprobadas (0 si no hay)."""
        resultado = self.resenas.filter(aprobada=True).aggregate(promedio=Avg('calificacion'))
        return round(resultado['promedio'] or 0, 1)

    @property
    def total_resenas(self):
        return self.resenas.filter(aprobada=True).count()

    @property
    def total_favoritos(self):
        return self.favoritos.count()

    @property
    def estrellas_llenas(self):
        """Lista para pintar estrellas en la plantilla: [1..5] llenas."""
        return range(int(round(self.calificacion_promedio)))

    @property
    def estrellas_vacias(self):
        return range(5 - int(round(self.calificacion_promedio)))


class ImagenProducto(models.Model):
    """Imágenes adicionales para la galería de un producto."""
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='productos/galeria/')
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Imagen de producto'
        verbose_name_plural = 'Imágenes de producto'
        ordering = ['orden']

    def __str__(self):
        return f'Imagen de {self.producto.nombre}'


class Resena(models.Model):
    """Reseña y calificación de un producto escrita por un cliente."""

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='resenas')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resenas'
    )
    calificacion = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Calificación de 1 a 5 estrellas.'
    )
    comentario = models.TextField()
    aprobada = models.BooleanField(
        default=True,
        help_text='Desmarcar para ocultar la reseña de la tienda.'
    )
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reseña'
        verbose_name_plural = 'Reseñas'
        ordering = ['-creada']
        # Un usuario solo puede reseñar cada producto una vez.
        constraints = [
            models.UniqueConstraint(
                fields=['producto', 'usuario'], name='resena_unica_por_usuario'
            )
        ]

    def __str__(self):
        return f'{self.usuario.username} — {self.producto.nombre} ({self.calificacion}★)'

    @property
    def estrellas_llenas(self):
        return range(self.calificacion)

    @property
    def estrellas_vacias(self):
        return range(5 - self.calificacion)


class Favorito(models.Model):
    """Producto guardado en la lista de deseos de un usuario."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favoritos'
    )
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='favoritos')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Favorito'
        verbose_name_plural = 'Favoritos'
        ordering = ['-creado']
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'producto'], name='favorito_unico_por_usuario'
            )
        ]

    def __str__(self):
        return f'{self.usuario.username} ♥ {self.producto.nombre}'


class Suscriptor(models.Model):
    """Correo suscrito al newsletter desde el pie de la página."""

    email = models.EmailField(unique=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Suscriptor'
        verbose_name_plural = 'Suscriptores'
        ordering = ['-creado']

    def __str__(self):
        return self.email
