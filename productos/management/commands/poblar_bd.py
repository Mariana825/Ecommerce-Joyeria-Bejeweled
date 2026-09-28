"""
Comando para llenar la base de datos con datos de prueba.

Uso:
    python manage.py poblar_bd           # agrega los datos
    python manage.py poblar_bd --limpiar # borra los datos de prueba y los vuelve a crear

Crea:
    - 5 categorías, 6 materiales, 4 colecciones
    - 20 productos (con stock, agotados, destacados y nuevos), cada uno con
      su propia imagen de producto (ver productos/fixtures/imagenes_productos/)
    - 1 usuario de prueba con perfil y 2 direcciones
    - 6 favoritos y 6 reseñas de ese usuario
    - 1 pedido con 3 artículos
    - 3 suscriptores al newsletter
"""

from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from pedidos.models import Pedido, PedidoItem
from productos.models import (
    Categoria, Coleccion, Favorito, Material, Producto, Resena, Suscriptor,
)

DIR_IMAGENES_PRODUCTOS = Path(__file__).resolve().parent.parent.parent / 'fixtures' / 'imagenes_productos'

from usuarios.models import DireccionEnvio

USUARIO_PRUEBA = 'mariana'
PASSWORD_PRUEBA = 'joyeria2026'


class Command(BaseCommand):
    help = 'Llena la base de datos con datos de prueba para la tienda de joyas.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Borra los datos de prueba antes de crearlos de nuevo.',
        )

    # ------------------------------------------------------------------
    @transaction.atomic
    def handle(self, *args, **opciones):
        if opciones['limpiar']:
            self._limpiar()

        categorias = self._crear_categorias()
        materiales = self._crear_materiales()
        colecciones = self._crear_colecciones()
        productos = self._crear_productos(categorias, materiales, colecciones)
        usuario, direcciones = self._crear_usuario()
        self._crear_favoritos(usuario, productos)
        self._crear_resenas(usuario, productos)
        self._crear_pedido(usuario, direcciones[0], productos)
        self._crear_suscriptores()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('¡Base de datos poblada correctamente!'))
        self.stdout.write('')
        self.stdout.write(f'  Usuario de prueba : {USUARIO_PRUEBA}')
        self.stdout.write(f'  Contraseña        : {PASSWORD_PRUEBA}')
        self.stdout.write('')
        self.stdout.write('  Tienda: http://127.0.0.1:8000/')
        self.stdout.write('  Admin : http://127.0.0.1:8000/admin/')
        self.stdout.write('')

    # ------------------------------------------------------------------
    def _limpiar(self):
        self.stdout.write('Borrando datos de prueba...')
        PedidoItem.objects.all().delete()
        Pedido.objects.all().delete()
        Resena.objects.all().delete()
        Favorito.objects.all().delete()
        self._borrar_imagenes_productos()
        Producto.objects.all().delete()
        Coleccion.objects.all().delete()
        Categoria.objects.all().delete()
        Material.objects.all().delete()
        Suscriptor.objects.all().delete()
        DireccionEnvio.objects.filter(usuario__username=USUARIO_PRUEBA).delete()
        User.objects.filter(username=USUARIO_PRUEBA).delete()
        self.stdout.write(self.style.WARNING('  Datos anteriores eliminados.'))

    def _borrar_imagenes_productos(self):
        """
        Borra del disco las imágenes que quedaron guardadas para los
        productos de prueba, para que `--limpiar` sea repetible sin ir
        acumulando copias con sufijos (imagen_abc123.jpg, imagen_xyz789.jpg...).
        """
        for producto in Producto.objects.exclude(imagen_principal=''):
            producto.imagen_principal.delete(save=False)

    # ------------------------------------------------------------------
    def _crear_categorias(self):
        datos = [
            ('Anillos', 'Anillos de compromiso, de boda y de uso diario.'),
            ('Collares', 'Collares y gargantillas en distintos materiales y largos.'),
            ('Pulseras', 'Pulseras finas, de eslabones y tejidas a mano.'),
            ('Aretes', 'Aretes de broquel, argollas y colgantes.'),
            ('Dijes', 'Dijes y charms para personalizar tus joyas.'),
        ]
        categorias = {}
        for nombre, descripcion in datos:
            obj, creado = Categoria.objects.get_or_create(
                nombre=nombre, defaults={'descripcion': descripcion, 'activa': True}
            )
            categorias[nombre] = obj
        self.stdout.write(f'  Categorías: {len(categorias)}')
        return categorias

    def _crear_materiales(self):
        nombres = [
            'Oro 18k', 'Oro 14k', 'Oro blanco', 'Plata 925',
            'Acero inoxidable', 'Chapa de oro',
        ]
        materiales = {}
        for nombre in nombres:
            obj, _ = Material.objects.get_or_create(nombre=nombre)
            materiales[nombre] = obj
        self.stdout.write(f'  Materiales: {len(materiales)}')
        return materiales

    def _crear_colecciones(self):
        datos = [
            ('Colección Dorada',
             'Piezas bañadas en oro 18K para quienes aprecian el lujo sin concesiones.',
             '#C9A84C', 1),
            ('Elegancia en Plata',
             'Diseños contemporáneos en plata esterlina 925. Sutileza redefinida.',
             '#A8AAAD', 2),
            ('Regalos Especiales',
             'Curada con amor para momentos que merecen ser recordados eternamente.',
             '#8A74A8', 3),
            ('Novias 2026',
             'Piezas pensadas para el día más importante: sobrias, luminosas y atemporales.',
             '#E8D28A', 4),
        ]
        colecciones = {}
        for nombre, descripcion, color, orden in datos:
            obj, _ = Coleccion.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'descripcion': descripcion,
                    'color_acento': color,
                    'orden': orden,
                    'activa': True,
                },
            )
            colecciones[nombre] = obj
        self.stdout.write(f'  Colecciones: {len(colecciones)}')
        return colecciones

    # ------------------------------------------------------------------
    def _crear_productos(self, cat, mat, col):
        # (nombre, categoría, material, colección, precio, existencias,
        #  destacado, es_nuevo, activo, descripción)
        datos = [
            ('Anillo Solitario Lumière', 'Anillos', 'Oro blanco', 'Novias 2026',
             '14900.00', 4, True, False, True,
             'Anillo solitario en oro blanco de 18k con diamante de talla brillante. '
             'El clásico absoluto para una pedida de mano.'),
            ('Anillo Trenzado Vienne', 'Anillos', 'Plata 925', 'Elegancia en Plata',
             '890.00', 24, False, True, True,
             'Anillo de plata 925 con diseño trenzado a mano. Ligero y cómodo para uso diario.'),
            ('Anillo Eternity Dorado', 'Anillos', 'Oro 18k', 'Colección Dorada',
             '9800.00', 6, True, False, True,
             'Banda completa de oro 18k con circonias engastadas en todo el contorno.'),
            ('Anillo Sello Clásico', 'Anillos', 'Oro 14k', 'Colección Dorada',
             '5400.00', 9, False, False, True,
             'Anillo tipo sello en oro 14k, disponible para grabado personalizado.'),
            ('Anillo Minimal Acero', 'Anillos', 'Acero inoxidable', None,
             '390.00', 45, False, True, True,
             'Anillo delgado de acero inoxidable, resistente al agua y al uso diario.'),

            ('Collar Cadena Veneciana', 'Collares', 'Oro 14k', 'Colección Dorada',
             '6200.00', 10, True, False, True,
             'Collar de oro 14k con tejido veneciano de 45 cm. Ligero, firme y elegante.'),
            ('Gargantilla Minimalista', 'Collares', 'Plata 925', 'Elegancia en Plata',
             '1150.00', 18, False, True, True,
             'Gargantilla de plata 925 con dije circular. Perfecta para combinar en capas.'),
            ('Collar Eternal Rose', 'Collares', 'Oro 18k', 'Regalos Especiales',
             '12850.00', 3, True, False, True,
             'Collar de oro 18k con dije en forma de rosa y rubí central. Pieza de edición limitada.'),
            ('Collar Perla Solitaria', 'Collares', 'Oro blanco', 'Novias 2026',
             '4600.00', 7, False, False, True,
             'Perla cultivada de agua dulce montada en cadena de oro blanco de 42 cm.'),
            ('Collar Capas Doradas', 'Collares', 'Chapa de oro', None,
             '760.00', 0, False, False, True,
             'Set de tres cadenas de distinto largo en chapa de oro, listas para usar en capas.'),

            ('Pulsera Tenis Céleste', 'Pulseras', 'Oro blanco', 'Novias 2026',
             '18400.00', 2, True, False, True,
             'Pulsera tenis en oro blanco con circonias de corte brillante y broche de seguridad doble.'),
            ('Pulsera de Eslabones', 'Pulseras', 'Acero inoxidable', None,
             '650.00', 32, False, False, True,
             'Pulsera de acero inoxidable resistente al agua, con broche de seguridad.'),
            ('Pulsera Soleil', 'Pulseras', 'Oro 18k', 'Colección Dorada',
             '7980.00', 5, False, True, True,
             'Pulsera de oro 18k con zafiro central engastado. Ajustable de 16 a 19 cm.'),
            ('Esclava Grabable', 'Pulseras', 'Plata 925', 'Regalos Especiales',
             '1390.00', 14, False, False, True,
             'Esclava de plata 925 con placa lisa lista para grabar nombre o fecha.'),
            ('Pulsera Hilo Rojo', 'Pulseras', 'Chapa de oro', 'Regalos Especiales',
             '290.00', 60, False, True, True,
             'Hilo rojo tejido con dije en chapa de oro. Un detalle pequeño y significativo.'),

            ('Aretes Argolla Pequeños', 'Aretes', 'Chapa de oro', None,
             '420.00', 48, False, False, True,
             'Argollas de 15 mm en chapa de oro. Ligeras y cómodas para todo el día.'),
            ('Aretes Broquel Perla', 'Aretes', 'Plata 925', 'Elegancia en Plata',
             '980.00', 16, False, False, True,
             'Broqueles de plata 925 con perla cultivada de agua dulce de 7 mm.'),
            ('Aretes Céleste Aguamarina', 'Aretes', 'Plata 925', 'Elegancia en Plata',
             '1120.00', 11, True, True, True,
             'Aretes de plata 925 con aguamarina de talla gota. Cierre de presión seguro.'),

            ('Dije Corazón Grabable', 'Dijes', 'Plata 925', 'Regalos Especiales',
             '560.00', 28, False, False, True,
             'Dije de plata en forma de corazón, disponible para grabado personalizado.'),
            ('Dije Inicial Oro', 'Dijes', 'Oro 14k', 'Regalos Especiales',
             '2300.00', 0, False, False, True,
             'Dije con letra inicial en oro 14k. Se vende por pieza, cadena no incluida.'),
        ]

        productos = []
        for (nombre, categoria, material, coleccion, precio, existencias,
             destacado, es_nuevo, activo, descripcion) in datos:
            obj, _ = Producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'categoria': cat[categoria],
                    'material': mat[material],
                    'coleccion': col[coleccion] if coleccion else None,
                    'descripcion': descripcion,
                    'precio': Decimal(precio),
                    'existencias': existencias,
                    'destacado': destacado,
                    'es_nuevo': es_nuevo,
                    'activo': activo,
                },
            )
            self._asignar_imagen(obj, nombre)
            productos.append(obj)

        con_imagen = sum(1 for p in productos if p.imagen_principal)
        agotados = sum(1 for p in productos if p.existencias == 0)
        self.stdout.write(
            f'  Productos: {len(productos)} '
            f'({sum(1 for p in productos if p.destacado)} destacados, {agotados} agotados, '
            f'{con_imagen} con imagen)'
        )
        return productos

    def _asignar_imagen(self, producto, nombre):
        """
        Asigna la imagen de producto correspondiente (generada de antemano,
        una distinta para cada pieza — ver productos/fixtures/imagenes_productos/)
        si el producto todavía no tiene una.
        """
        if producto.imagen_principal:
            return

        archivo = DIR_IMAGENES_PRODUCTOS / f'{slugify(nombre)}.jpg'
        if not archivo.exists():
            self.stdout.write(self.style.WARNING(f'  Sin imagen de prueba para "{nombre}" ({archivo.name})'))
            return

        with archivo.open('rb') as f:
            producto.imagen_principal.save(archivo.name, File(f), save=True)

    # ------------------------------------------------------------------
    def _crear_usuario(self):
        usuario, creado = User.objects.get_or_create(
            username=USUARIO_PRUEBA,
            defaults={
                'first_name': 'Mariana',
                'last_name': 'Rivera',
                'email': 'mariana@ejemplo.com',
            },
        )
        if creado:
            usuario.set_password(PASSWORD_PRUEBA)
            usuario.save()

        # El perfil lo crea automáticamente la señal post_save del modelo Perfil.
        perfil = usuario.perfil
        perfil.telefono = '5512345678'
        perfil.save()

        direcciones = []
        datos_direcciones = [
            {
                'etiqueta': 'Casa', 'destinatario': 'Mariana Rivera',
                'calle': 'Av. Paseo de la Reforma', 'numero': '222',
                'colonia': 'Juárez', 'ciudad': 'Ciudad de México',
                'estado': 'Ciudad de México', 'codigo_postal': '06600',
                'pais': 'México', 'telefono_contacto': '5512345678',
                'predeterminada': True,
            },
            {
                'etiqueta': 'Oficina', 'destinatario': 'Mariana Rivera',
                'calle': 'Calle Río Lerma', 'numero': '45',
                'colonia': 'Cuauhtémoc', 'ciudad': 'Ciudad de México',
                'estado': 'Ciudad de México', 'codigo_postal': '06500',
                'pais': 'México', 'telefono_contacto': '5598765432',
                'predeterminada': False,
            },
        ]
        for datos in datos_direcciones:
            direccion, _ = DireccionEnvio.objects.get_or_create(
                usuario=usuario, etiqueta=datos['etiqueta'], defaults=datos
            )
            direcciones.append(direccion)

        self.stdout.write(f'  Usuario: {usuario.username} (con {len(direcciones)} direcciones)')
        return usuario, direcciones

    # ------------------------------------------------------------------
    def _crear_favoritos(self, usuario, productos):
        # Guardamos como favoritos algunos productos de distintas categorías.
        for producto in [productos[0], productos[5], productos[7], productos[10],
                         productos[17], productos[18]]:
            Favorito.objects.get_or_create(usuario=usuario, producto=producto)
        self.stdout.write(f'  Favoritos: {usuario.favoritos.count()}')

    def _crear_resenas(self, usuario, productos):
        # Un usuario solo puede reseñar cada producto una vez, así que cada
        # reseña va a un producto distinto.
        datos = [
            (productos[0], 5, 'El engaste es impecable y el brillo del diamante se nota '
                              'muchísimo en persona. Llegó en una caja preciosa.'),
            (productos[5], 4, 'La cadena es bonita y bien hecha, aunque me habría gustado '
                              'que trajera unos centímetros más de largo.'),
            (productos[7], 5, 'Es la pieza más linda que tengo. El rubí tiene un color '
                              'intenso y el acabado de la rosa está increíble.'),
            (productos[10], 5, 'Vale cada peso. El broche doble da mucha seguridad y no se '
                               'siente pesada al usarla todo el día.'),
            (productos[17], 4, 'Los aretes son delicados y el color de la aguamarina es '
                               'exactamente como en las fotos. Muy cómodos.'),
            (productos[18], 3, 'El dije está bien por el precio, pero el grabado quedó un '
                               'poco más ligero de lo que esperaba.'),
        ]
        for producto, calificacion, comentario in datos:
            Resena.objects.get_or_create(
                producto=producto, usuario=usuario,
                defaults={
                    'calificacion': calificacion,
                    'comentario': comentario,
                    'aprobada': True,
                },
            )
        self.stdout.write(f'  Reseñas: {Resena.objects.count()}')

    # ------------------------------------------------------------------
    def _crear_pedido(self, usuario, direccion, productos):
        if Pedido.objects.filter(usuario=usuario).exists():
            self.stdout.write('  Pedido: ya existía, no se creó otro')
            return

        pedido = Pedido.objects.create(
            usuario=usuario,
            direccion_envio=direccion,
            nombre_destinatario=direccion.destinatario,
            calle=direccion.calle,
            numero=direccion.numero,
            colonia=direccion.colonia,
            ciudad=direccion.ciudad,
            estado_direccion=direccion.estado,
            codigo_postal=direccion.codigo_postal,
            pais=direccion.pais,
            telefono_contacto=direccion.telefono_contacto,
            estado=Pedido.Estado.PENDIENTE_PAGO,
        )

        # 3 artículos, descontando el inventario como lo hace el checkout real.
        articulos = [(productos[6], 1), (productos[15], 2), (productos[18], 1)]
        for producto, cantidad in articulos:
            PedidoItem.objects.create(
                pedido=pedido,
                producto=producto,
                nombre_producto=producto.nombre,
                precio_unitario=producto.precio,
                cantidad=cantidad,
            )
            producto.existencias = max(0, producto.existencias - cantidad)
            producto.save(update_fields=['existencias'])

        self.stdout.write(
            f'  Pedido: #{pedido.pk} con {len(articulos)} artículos — total ${pedido.total}'
        )

    # ------------------------------------------------------------------
    def _crear_suscriptores(self):
        for email in ['ana@ejemplo.com', 'lucia@ejemplo.com', 'sofia@ejemplo.com']:
            Suscriptor.objects.get_or_create(email=email)
        self.stdout.write(f'  Suscriptores: {Suscriptor.objects.count()}')
