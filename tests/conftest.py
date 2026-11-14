"""Fixtures compartidos por todas las pruebas unitarias de Bejeweled."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from pedidos.models import Pedido, PedidoItem
from productos.models import Categoria, Material, Producto
from usuarios.models import DireccionEnvio

User = get_user_model()


@pytest.fixture(autouse=True)
def entorno_aislado(monkeypatch):
    """
    Aísla cada prueba:
    - limpia la caché y el estado global del módulo de traducción;
    - bloquea cualquier petición HTTP real por descuido (si una prueba olvida
      mockear `requests`, falla de forma ruidosa en vez de salir a internet).
    """
    from traduccion import services

    cache.clear()
    services._TRADUCCIONES_CARGADAS.clear()
    services._PARES_YA_INTENTADOS.clear()

    def _sin_red(*args, **kwargs):
        raise AssertionError('La prueba intentó hacer una petición HTTP real; mockea requests.')

    monkeypatch.setattr('requests.sessions.Session.request', _sin_red)
    yield
    cache.clear()


# ----------------------------------------------------------------- usuarios
@pytest.fixture
def crear_usuario():
    contador = {'n': 0}

    def _crear(username=None, **extra):
        contador['n'] += 1
        username = username or f'usuario{contador["n"]}'
        extra.setdefault('email', f'{username}@example.com')
        return User.objects.create_user(username=username, password='Clave-segura-2026', **extra)

    return _crear


@pytest.fixture
def usuario(crear_usuario):
    return crear_usuario('cliente1')


@pytest.fixture
def otro_usuario(crear_usuario):
    return crear_usuario('cliente2')


@pytest.fixture
def cliente_autenticado(client, usuario):
    client.force_login(usuario)
    return client


@pytest.fixture
def direccion(usuario):
    return DireccionEnvio.objects.create(
        usuario=usuario, etiqueta='Casa', destinatario='Mariana López',
        calle='Av. Reforma', numero='100', colonia='Centro', ciudad='CDMX',
        estado='CDMX', codigo_postal='06000', pais='México',
        telefono_contacto='5555555555',
    )


# ----------------------------------------------------------------- catálogo
@pytest.fixture
def categoria():
    return Categoria.objects.create(nombre='Anillos')


@pytest.fixture
def material():
    return Material.objects.create(nombre='Oro 18k')


@pytest.fixture
def crear_producto(categoria):
    contador = {'n': 0}

    def _crear(nombre=None, precio='1000.00', existencias=10, **extra):
        contador['n'] += 1
        extra.setdefault('categoria', categoria)
        return Producto.objects.create(
            nombre=nombre or f'Producto {contador["n"]}',
            precio=Decimal(str(precio)), existencias=existencias, **extra,
        )

    return _crear


@pytest.fixture
def producto(crear_producto):
    return crear_producto('Anillo Solitario', precio='1000.00', existencias=10)


# ------------------------------------------------------------------ pedidos
@pytest.fixture
def crear_pedido():
    def _crear(usuario, items=(), **extra):
        pedido = Pedido.objects.create(
            usuario=usuario, nombre_destinatario='Mariana López', calle='Av. Reforma',
            ciudad='CDMX', estado_direccion='CDMX', codigo_postal='06000',
            pais='México', **extra,
        )
        for producto, cantidad in items:
            PedidoItem.objects.create(
                pedido=pedido, producto=producto, nombre_producto=producto.nombre,
                precio_unitario=producto.precio, cantidad=cantidad,
            )
        return pedido

    return _crear


# ---------------------------------------------------------------- utilidades
@pytest.fixture
def fabrica_respuesta():
    """Construye respuestas HTTP falsas (como las de `requests`)."""

    def _crear(status=200, datos=None, texto=''):
        respuesta = Mock()
        respuesta.status_code = status
        respuesta.ok = 200 <= status < 400
        respuesta.text = texto
        respuesta.content = b'{}' if datos is not None else b''
        respuesta.json.return_value = datos if datos is not None else {}
        respuesta.raise_for_status.return_value = None
        return respuesta

    return _crear


@pytest.fixture
def api_cliente(settings):
    """Cliente DRF que ya manda la API key correcta."""
    cliente = APIClient()
    cliente.credentials(HTTP_X_API_KEY=settings.INVENTARIO_API_KEY)
    return cliente


@pytest.fixture
def respuesta_gemini():
    return lambda texto: SimpleNamespace(text=texto)
