"""Productos y catálogo: TU-06 a TU-09 (+ extras EX-03 a EX-06)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.forms import modelform_factory
from django.urls import reverse

from productos.models import Categoria, Coleccion, Material, Producto

pytestmark = pytest.mark.django_db


# ----------------------------------------------------------------- TU-06
def test_tu06_crea_producto_valido(categoria, material):
    producto = Producto(
        nombre='Anillo Solitario', categoria=categoria, material=material,
        precio=Decimal('1999.90'), existencias=5,
    )
    producto.full_clean()  # no debe lanzar ValidationError
    producto.save()
    producto.refresh_from_db()

    assert producto.slug == 'anillo-solitario'
    assert producto.precio == Decimal('1999.90')
    assert producto.existencias == 5
    assert producto.activo is True       # visible por defecto
    assert producto.destacado is False
    assert str(producto) == 'Anillo Solitario'
    assert producto.get_absolute_url() == reverse('productos:detalle', args=['anillo-solitario'])


# ----------------------------------------------------------------- TU-07
@pytest.mark.xfail(
    strict=True,
    reason='BRECHA DETECTADA: Producto.precio no tiene validador de mínimo y acepta precios '
           'negativos. Agrega validators=[MinValueValidator(Decimal("0.01"))] al campo (y una '
           'migración); esta prueba empezará a pasar y entonces quita el xfail.',
)
def test_tu07_rechaza_precio_negativo(categoria):
    producto = Producto(nombre='Anillo', categoria=categoria,
                        precio=Decimal('-10.00'), existencias=1)

    with pytest.raises(ValidationError) as error:
        producto.full_clean()
    assert 'precio' in error.value.message_dict


# ----------------------------------------------------------------- TU-08
# Nota: con SQLite, Django no añade validador de mínimo al modelo (full_clean() no detecta
# existencias negativas); la protección real está en el formulario (admin) y en la restricción
# CHECK de la base de datos. Se prueban ambas capas.
FormularioProducto = modelform_factory(
    Producto, fields=['nombre', 'categoria', 'precio', 'existencias'])


def test_tu08_el_formulario_rechaza_existencias_negativas(categoria):
    form = FormularioProducto({'nombre': 'Anillo', 'categoria': categoria.pk,
                               'precio': '10.00', 'existencias': -1})

    assert not form.is_valid()
    assert 'existencias' in form.errors


def test_tu08b_la_base_de_datos_tambien_rechaza_existencias_negativas(categoria):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Producto.objects.create(nombre='Anillo', categoria=categoria,
                                    precio=Decimal('10.00'), existencias=-1)


def test_tu08c_el_formulario_acepta_cero_existencias(categoria):
    form = FormularioProducto({'nombre': 'Anillo', 'categoria': categoria.pk,
                               'precio': '10.00', 'existencias': 0})

    assert form.is_valid(), form.errors


# ----------------------------------------------------------------- TU-09
def test_tu09_relaciones_con_categoria_material_y_coleccion(crear_producto):
    categoria = Categoria.objects.create(nombre='Collares')
    material = Material.objects.create(nombre='Plata 925')
    coleccion = Coleccion.objects.create(nombre='Luna')
    producto = crear_producto('Collar Luna', categoria=categoria, material=material,
                              coleccion=coleccion)

    assert producto.categoria == categoria
    assert producto.material == material
    assert producto.coleccion == coleccion
    assert list(categoria.productos.all()) == [producto]
    assert list(material.productos.all()) == [producto]
    assert list(coleccion.productos.all()) == [producto]
    assert categoria.slug == 'collares'  # slug automático


def test_tu09b_al_borrar_categoria_o_material_el_producto_se_conserva(crear_producto):
    categoria = Categoria.objects.create(nombre='Pulseras')
    material = Material.objects.create(nombre='Acero')
    producto = crear_producto('Pulsera', categoria=categoria, material=material)

    categoria.delete()
    material.delete()
    producto.refresh_from_db()

    assert producto.categoria is None
    assert producto.material is None


# ------------------------------------------------------------------ EXTRAS
def test_ex03_slug_se_hace_unico_cuando_el_nombre_se_repite(crear_producto):
    primero = crear_producto('Anillo de Oro')
    segundo = crear_producto('Anillo de Oro')
    tercero = crear_producto('Anillo de Oro')

    assert [primero.slug, segundo.slug, tercero.slug] == [
        'anillo-de-oro', 'anillo-de-oro-2', 'anillo-de-oro-3']


@pytest.mark.parametrize('activo, existencias, esperado', [
    (True, 3, True),
    (True, 0, False),    # agotado
    (False, 3, False),   # oculto en la tienda
    (False, 0, False),
])
def test_ex04_disponible_requiere_activo_y_existencias(crear_producto, activo, existencias, esperado):
    producto = crear_producto(activo=activo, existencias=existencias)
    assert producto.disponible is esperado


def test_ex05_catalogo_solo_muestra_productos_activos(client, crear_producto):
    visible = crear_producto('Visible')
    oculto = crear_producto('Oculto', activo=False)

    respuesta = client.get(reverse('productos:catalogo'))
    ids = [p.id for p in respuesta.context['productos']]

    assert visible.id in ids
    assert oculto.id not in ids


def test_ex06_catalogo_filtros_de_busqueda_precio_y_disponibilidad(client, crear_producto):
    barato = crear_producto('Aro de plata', precio='100.00', existencias=5)
    caro = crear_producto('Anillo de oro', precio='5000.00', existencias=5)
    agotado = crear_producto('Anillo agotado', precio='300.00', existencias=0)
    url = reverse('productos:catalogo')

    def ids(**params):
        return {p.id for p in client.get(url, params).context['productos']}

    assert ids(q='anillo') == {caro.id, agotado.id}
    assert ids(precio_min='200') == {caro.id, agotado.id}
    assert ids(precio_max='200') == {barato.id}
    assert ids(disponibles='1') == {barato.id, caro.id}


def test_ex06b_catalogo_ordena_por_precio(client, crear_producto):
    crear_producto('B', precio='300.00')
    crear_producto('A', precio='100.00')
    crear_producto('C', precio='200.00')

    respuesta = client.get(reverse('productos:catalogo'), {'orden': 'precio_asc'})

    assert [p.precio for p in respuesta.context['productos']] == [
        Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]


def test_ex06c_detalle_de_producto_inactivo_devuelve_404(client, crear_producto):
    oculto = crear_producto('Oculto', activo=False)

    assert client.get(oculto.get_absolute_url()).status_code == 404
