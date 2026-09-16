from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ResenaForm, SuscriptorForm
from .models import Categoria, Coleccion, Favorito, Material, Producto, Suscriptor


def _ids_favoritos(request):
    """IDs de productos marcados como favoritos por el usuario actual."""
    if request.user.is_authenticated:
        return set(request.user.favoritos.values_list('producto_id', flat=True))
    return set()


# ============================================================
#  Página principal (landing)
# ============================================================
def inicio(request):
    destacados = Producto.objects.filter(
        activo=True, destacado=True
    ).select_related('categoria', 'material')[:4]

    # Si aún no hay productos marcados como destacados, mostramos los más recientes.
    if not destacados:
        destacados = Producto.objects.filter(activo=True).select_related(
            'categoria', 'material'
        )[:4]

    contexto = {
        'categorias': Categoria.objects.filter(activa=True)[:4],
        'destacados': destacados,
        'colecciones': Coleccion.objects.filter(activa=True)[:3],
        'favoritos_ids': _ids_favoritos(request),
    }
    return render(request, 'productos/inicio.html', contexto)


# ============================================================
#  Catálogo
# ============================================================
def catalogo(request):
    productos = Producto.objects.filter(activo=True).select_related('categoria', 'material')

    # --- Búsqueda ---
    q = request.GET.get('q', '').strip()
    if q:
        productos = productos.filter(
            Q(nombre__icontains=q) | Q(descripcion__icontains=q)
        )

    # --- Filtro por categoría ---
    categoria_slug = request.GET.get('categoria', '')
    if categoria_slug:
        productos = productos.filter(categoria__slug=categoria_slug)

    # --- Filtro por material ---
    material_id = request.GET.get('material', '')
    if material_id.isdigit():
        productos = productos.filter(material_id=material_id)

    # --- Filtro por rango de precio ---
    precio_min = request.GET.get('precio_min', '')
    precio_max = request.GET.get('precio_max', '')
    if precio_min.replace('.', '', 1).isdigit():
        productos = productos.filter(precio__gte=precio_min)
    if precio_max.replace('.', '', 1).isdigit():
        productos = productos.filter(precio__lte=precio_max)

    # --- Solo disponibles ---
    solo_disponibles = request.GET.get('disponibles') == '1'
    if solo_disponibles:
        productos = productos.filter(existencias__gt=0)

    # --- Orden ---
    orden = request.GET.get('orden', '')
    opciones_orden = {
        'precio_asc': 'precio',
        'precio_desc': '-precio',
        'nombre': 'nombre',
        'recientes': '-creado',
    }
    productos = productos.order_by(opciones_orden.get(orden, '-creado'))

    total_resultados = productos.count()

    paginador = Paginator(productos, 12)
    productos_paginados = paginador.get_page(request.GET.get('pagina'))

    # Conserva los filtros al cambiar de página, sin duplicar el parámetro "pagina".
    params = request.GET.copy()
    params.pop('pagina', None)

    contexto = {
        'productos': productos_paginados,
        'total_resultados': total_resultados,
        'categorias': Categoria.objects.filter(activa=True),
        'materiales': Material.objects.all(),
        'q': q,
        'categoria_actual': categoria_slug,
        'material_actual': material_id,
        'precio_min': precio_min,
        'precio_max': precio_max,
        'orden_actual': orden,
        'solo_disponibles': solo_disponibles,
        'query_string': params.urlencode(),
        'favoritos_ids': _ids_favoritos(request),
    }
    return render(request, 'productos/catalogo.html', contexto)


def detalle(request, slug):
    producto = get_object_or_404(
        Producto.objects.select_related('categoria', 'material', 'coleccion'),
        slug=slug, activo=True,
    )
    relacionados = Producto.objects.filter(
        categoria=producto.categoria, activo=True
    ).exclude(pk=producto.pk)[:4]

    resenas = producto.resenas.filter(aprobada=True).select_related('usuario')

    # ¿El usuario ya reseñó este producto?
    resena_propia = None
    if request.user.is_authenticated:
        resena_propia = producto.resenas.filter(usuario=request.user).first()

    contexto = {
        'producto': producto,
        'relacionados': relacionados,
        'resenas': resenas,
        'resena_propia': resena_propia,
        'form_resena': ResenaForm() if not resena_propia else None,
        'favoritos_ids': _ids_favoritos(request),
    }
    return render(request, 'productos/detalle.html', contexto)


# ============================================================
#  Colecciones
# ============================================================
def lista_colecciones(request):
    return render(request, 'productos/colecciones.html', {
        'colecciones': Coleccion.objects.filter(activa=True),
    })


def detalle_coleccion(request, slug):
    coleccion = get_object_or_404(Coleccion, slug=slug, activa=True)
    productos = coleccion.productos.filter(activo=True).select_related('categoria', 'material')

    return render(request, 'productos/coleccion_detalle.html', {
        'coleccion': coleccion,
        'productos': productos,
        'favoritos_ids': _ids_favoritos(request),
    })


# ============================================================
#  Favoritos (lista de deseos)
# ============================================================
@login_required
def mis_favoritos(request):
    favoritos = request.user.favoritos.select_related(
        'producto', 'producto__categoria', 'producto__material'
    )
    return render(request, 'productos/favoritos.html', {
        'favoritos': favoritos,
        'favoritos_ids': _ids_favoritos(request),
    })


@login_required
@require_POST
def alternar_favorito(request, producto_id):
    """Agrega o quita un producto de favoritos y regresa a donde estaba el usuario."""
    producto = get_object_or_404(Producto, id=producto_id)
    favorito = Favorito.objects.filter(usuario=request.user, producto=producto).first()

    if favorito:
        favorito.delete()
        messages.info(request, f'"{producto.nombre}" se quitó de tus favoritos.')
    else:
        Favorito.objects.create(usuario=request.user, producto=producto)
        messages.success(request, f'"{producto.nombre}" se agregó a tus favoritos.')

    return redirect(request.POST.get('siguiente') or 'productos:catalogo')


# ============================================================
#  Reseñas
# ============================================================
@login_required
@require_POST
def crear_resena(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id, activo=True)

    if producto.resenas.filter(usuario=request.user).exists():
        messages.warning(request, 'Ya escribiste una reseña para este producto.')
        return redirect(producto.get_absolute_url())

    form = ResenaForm(request.POST)
    if form.is_valid():
        resena = form.save(commit=False)
        resena.producto = producto
        resena.usuario = request.user
        resena.save()
        messages.success(request, '¡Gracias! Tu reseña se publicó correctamente.')
    else:
        messages.error(request, 'Revisa los datos de tu reseña e inténtalo de nuevo.')

    return redirect(producto.get_absolute_url())


# ============================================================
#  Newsletter
# ============================================================
@require_POST
def suscribir_newsletter(request):
    email = request.POST.get('email', '').strip()

    if Suscriptor.objects.filter(email=email).exists():
        messages.info(request, 'Ese correo ya está suscrito a nuestro boletín.')
    else:
        form = SuscriptorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Listo! Te avisaremos de cada nueva colección.')
        else:
            messages.error(request, 'Ingresa un correo electrónico válido.')

    return redirect(request.POST.get('siguiente') or 'productos:inicio')
