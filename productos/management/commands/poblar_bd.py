"""
Comando para llenar la base de datos con datos de prueba de la tienda Bejeweled.

Uso:
    python manage.py poblar_bd                         # crea o actualiza los datos
    python manage.py poblar_bd --reemplazar-imagenes   # ademas cambia las fotos por las locales
    python manage.py poblar_bd --limpiar               # borra TODO lo de prueba y lo recrea

Imagenes:
    Coloca una foto por producto en <app>/fixtures/imagenes_productos/ con el
    nombre del producto en formato slug (anillo-solitario-lumiere.jpg, etc.).
    Acepta .jpg, .jpeg, .png y .webp. Si falta alguna, el comando avisa con la
    ruta exacta y el nombre de archivo que espera.

"""

from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from pedidos.models import Pedido, PedidoItem
from productos.models import (
    Categoria, Coleccion, Favorito, Material, Producto, Resena, Suscriptor,
)
from usuarios.models import DireccionEnvio

DIR_IMAGENES_PRODUCTOS = (
    Path(__file__).resolve().parent.parent.parent / 'fixtures' / 'imagenes_productos'
)
EXTENSIONES = ('.jpg', '.jpeg', '.png', '.webp')

USUARIO_PRUEBA = 'mariana'
PASSWORD_PRUEBA = 'joyeria2026'

# ---------------------------------------------------------------------------
#  Textos de cuidados y armado de la ficha tecnica
# ---------------------------------------------------------------------------
CUIDADO_ORO = 'Evita el contacto prolongado con cloro y perfumes y límpiala con un paño suave.'
CUIDADO_PLATA = ('Guárdala en una bolsa cerrada para que se oscurezca menos y límpiala '
                 'con un paño para plata.')
CUIDADO_BANO = ('El baño de oro se desgasta poco a poco con el roce, el agua, el sudor y los '
                'perfumes: retírala para bañarte o hacer ejercicio y guárdala seca.')
CUIDADO_PVD = ('Aunque el baño PVD resiste mejor el uso diario, evita productos abrasivos y '
               'perfumes y límpiala con un paño suave.')
CUIDADO_ACERO = 'Límpiala con agua tibia, jabón neutro y un paño suave.'
CUIDADO_PERLA = ('Las perlas son delicadas: colócala después del perfume y las cremas, y '
                 'límpiala con un paño suave y seco.')


def ficha(resumen, base, acabado, piedra=None, medidas=None, cuidados=None):
    """Arma la descripcion del producto con su ficha tecnica."""
    lineas = [resumen, '', f'Material base: {base}', f'Acabado: {acabado}']
    if piedra:
        lineas.append(f'Piedra: {piedra}')
    if medidas:
        lineas.append(f'Medidas: {medidas}')
    if cuidados:
        lineas.append(f'Cuidados: {cuidados}')
    return '\n'.join(lineas)


class Command(BaseCommand):
    help = 'Llena la base de datos con datos de prueba para la tienda de joyas.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Borra los datos de prueba antes de crearlos de nuevo.',
        )
        parser.add_argument(
            '--reemplazar-imagenes',
            action='store_true',
            dest='reemplazar_imagenes',
            help='Reemplaza la foto de cada producto por la del disco '
                 '(fixtures/imagenes_productos/<slug>.jpg).',
        )

    # ------------------------------------------------------------------
    @transaction.atomic
    def handle(self, *args, **opciones):
        self.reemplazar_imagenes = opciones['reemplazar_imagenes']
        self.imagenes_faltantes = 0

        self._silenciar_aviso_newsletter()

        if opciones['limpiar']:
            self._limpiar()

        categorias = self._crear_categorias()
        materiales = self._crear_materiales()
        colecciones = self._crear_colecciones()
        productos = self._crear_productos(categorias, materiales, colecciones)
        usuario, direcciones = self._crear_usuario()
        self._crear_resenas(usuario, productos)

        if self.imagenes_faltantes:
            self.stdout.write(self.style.WARNING(
                f'\n  Faltan {self.imagenes_faltantes} imagen(es). Carpeta esperada:\n'
                f'  {DIR_IMAGENES_PRODUCTOS}'
            ))
        self.stdout.write(self.style.SUCCESS(
            f'\nListo. Usuario de prueba: {USUARIO_PRUEBA} / {PASSWORD_PRUEBA}'
        ))

    # ------------------------------------------------------------------
    def _silenciar_aviso_newsletter(self):
        """Evita que crear productos de prueba mande correos a los suscriptores."""
        try:
            from django.db.models.signals import post_save
            from productos.signals import avisar_suscriptores
            post_save.disconnect(avisar_suscriptores, sender=Producto)
        except ImportError:
            pass  # todavia no existe la senal del newsletter

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
        Borra del disco las imagenes de los productos para que `--limpiar` sea
        repetible sin acumular copias con sufijos (imagen_abc123.jpg...).
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
            obj, _ = Categoria.objects.get_or_create(
                nombre=nombre, defaults={'descripcion': descripcion, 'activa': True}
            )
            categorias[nombre] = obj
        self.stdout.write(f'  Categorías: {len(categorias)}')
        return categorias

    def _crear_materiales(self):
        nombres = [
            'Oro amarillo 18k', 'Oro amarillo 14k', 'Oro blanco 18k', 'Oro blanco 14k',
            'Plata 925', 'Plata 925 con baño de oro',
            'Acero inoxidable 316L', 'Acero 316L con baño de oro (PVD)',
            'Latón con baño de oro',
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
            'Piezas en tonos dorados: oro macizo de 14k y 18k, y opciones con baño de oro '
            'para el uso diario.',
            '#C9A84C', 1, 'productos/coleccion-dorada.jpg'),
            ('Elegancia en Plata',
            'Diseños contemporáneos en plata 925, con baño de rodio y piedras naturales.',
            '#A8AAAD', 2, 'productos/coleccion-plata.jpg'),
            ('Regalos Especiales',
            'Curada con amor para momentos que merecen ser recordados: piezas para grabar, '
            'dijes y detalles personales.',
            '#8A74A8', 3, 'productos/coleccion-regalo.jpg'),
        ]
        colecciones = {}
        for nombre, descripcion, color, orden, imagen in datos:
            obj, _ = Coleccion.objects.update_or_create(
                nombre=nombre,
                defaults={
                    'descripcion': descripcion,
                    'color_acento': color,
                    'orden': orden,
                    'activa': True,
                    'imagen': imagen,
                },
            )
            colecciones[nombre] = obj
        self.stdout.write(f'  Colecciones: {len(colecciones)}')
        return colecciones

   
    def _crear_productos(self, cat, mat, col):
        # (nombre, categoria, material, coleccion, precio, existencias,
        #  destacado, es_nuevo, activo, descripcion)
        datos = [
            # ---------------- ANILLOS ----------------
            ('Anillo Solitario Lumière', 'Anillos', 'Oro blanco 18k', None,
             '14900.00', 4, True, False, True,
             ficha('Anillo solitario de líneas limpias con un diamante central de talla '
                   'brillante sostenido por cuatro garras. Pensado para una pedida de mano, '
                   'deja que la piedra sea la protagonista.',
                   'Oro blanco de 18 quilates (750)',
                   'Baño de rodio para un blanco más brillante y duradero',
                   'Diamante natural de 0.30 ct, talla brillante',
                   'Banda de 1.8 mm. Tallas 5 a 9',
                   CUIDADO_ORO)),
            ('Anillo Trenzado Vienne', 'Anillos', 'Plata 925', 'Elegancia en Plata',
             '890.00', 24, False, True, True,
             ficha('Anillo de plata con una banda de tres hilos trenzados a mano, de aspecto '
                   'artesanal y muy ligero. Se siente cómodo todo el día y combina bien con '
                   'otros anillos finos.',
                   'Plata 925 (92.5 % de plata pura)',
                   'Baño de rodio para retrasar el deslustre',
                   None,
                   'Banda de 3 mm. Tallas 5 a 10',
                   CUIDADO_PLATA)),
            ('Anillo Eternity Dorado', 'Anillos', 'Oro amarillo 18k', 'Colección Dorada',
             '9800.00', 6, True, False, True,
             ficha('Banda completa que recorre todo el contorno del dedo con circonias '
                   'engastadas una junto a otra. Un anillo luminoso que sirve como alianza '
                   'de boda o como regalo de aniversario.',
                   'Oro amarillo de 18 quilates (750)',
                   'Pulido de alto brillo (oro macizo, sin recubrimiento)',
                   'Circonias cúbicas de 1.5 mm en engaste de garras compartidas',
                   'Banda de 2 mm. Tallas 5 a 9',
                   CUIDADO_ORO)),
            ('Anillo Sello Clásico', 'Anillos', 'Oro amarillo 14k', 'Colección Dorada',
             '5400.00', 9, False, False, True,
             ficha('Anillo tipo sello de cara ovalada y brillo clásico, con espacio para '
                   'grabar iniciales o un símbolo. Una pieza que se hereda y se usa en el '
                   'meñique o en cualquier dedo.',
                   'Oro amarillo de 14 quilates (585)',
                   'Pulido (oro macizo, sin recubrimiento)',
                   None,
                   'Cara ovalada de 12 x 10 mm. Tallas 6 a 11',
                   CUIDADO_ORO)),
            ('Anillo Minimal Acero', 'Anillos', 'Acero inoxidable 316L', None,
             '390.00', 45, False, True, True,
             ficha('Anillo de banda delgada y diseño liso, pensado para el uso diario y para '
                   'combinar con otros anillos. El acero inoxidable 316L soporta bien el '
                   'contacto ocasional con el agua.',
                   'Acero inoxidable 316L',
                   'Pulido espejo; el color es el propio del acero, sin recubrimiento',
                   None,
                   'Banda de 2 mm. Tallas 5 a 11',
                   CUIDADO_ACERO)),

            # ---------------- COLLARES ----------------
            ('Collar Cadena Veneciana', 'Collares', 'Oro amarillo 14k', 'Colección Dorada',
             '6200.00', 10, True, False, True,
             ficha('Collar de cadena veneciana de eslabones cuadrados, firme y con mucho '
                   'brillo. Se usa solo o con un dije y es una pieza básica para toda la vida.',
                   'Oro amarillo de 14 quilates (585)',
                   'Pulido (oro macizo, sin recubrimiento)',
                   None,
                   'Largo de 45 cm, grosor de 1.2 mm, cierre de mosquetón',
                   CUIDADO_ORO)),
            ('Gargantilla Minimalista', 'Collares', 'Plata 925', 'Elegancia en Plata',
             '1150.00', 18, False, True, True,
             ficha('Gargantilla fina con un pequeño dije circular que descansa justo en la '
                   'clavícula. Es ligera y funciona muy bien para usar en capas con otros '
                   'collares.',
                   'Plata 925',
                   'Baño de rodio',
                   None,
                   'Largo ajustable de 35 a 40 cm. Dije circular de 10 mm',
                   CUIDADO_PLATA)),
            ('Collar Eternal Rose', 'Collares', 'Oro amarillo 18k', 'Regalos Especiales',
             '12850.00', 3, True, False, True,
             ficha('Dije en forma de rosa con un rubí en el centro de la flor y los pétalos '
                   'con textura satinada. Es una pieza de edición limitada pensada para '
                   'regalar en una fecha importante.',
                   'Oro amarillo de 18 quilates (750)',
                   'Pulido en la cadena y satinado en los pétalos (sin recubrimiento)',
                   'Rubí natural de 4 mm engastado al centro',
                   'Dije de 14 mm. Cadena de 45 cm con cierre de mosquetón',
                   CUIDADO_ORO)),
            ('Collar Perla Solitaria', 'Collares', 'Oro blanco 14k', None,
             '4600.00', 7, False, False, True,
             ficha('Una sola perla cultivada de agua dulce, de tono blanco cremoso, montada '
                   'sobre una cadena fina. Sobria y atemporal, es una opción clásica para '
                   'el uso diario.',
                   'Oro blanco de 14 quilates (585)',
                   'Baño de rodio',
                   'Perla cultivada de agua dulce de 8 mm',
                   'Cadena de 42 cm con 3 cm de extensión',
                   CUIDADO_PERLA)),
            ('Collar Capas Doradas', 'Collares', 'Latón con baño de oro', 'Colección Dorada',
             '760.00', 13, False, False, True,
             ficha('Set de tres cadenas finas de distinto largo, pensadas para usarse juntas '
                   'y lograr el efecto de capas sin tener que combinarlas tú. Una forma '
                   'accesible de llevar el dorado.',
                   'Latón',
                   'Baño de oro de 18 quilates',
                   None,
                   'Tres cadenas de 36, 42 y 50 cm',
                   CUIDADO_BANO)),

            # ---------------- PULSERAS ----------------
            ('Pulsera Tenis Céleste', 'Pulseras', 'Oro blanco 14k', 'Regalos Especiales',
             '18400.00', 2, True, False, True,
             ficha('Pulsera tipo tenis con una línea continua de diamantes del mismo tamaño '
                   'que atrapan la luz con cada movimiento. Es la pieza más lujosa de la '
                   'colección',
                   'Oro blanco de 14 quilates (585)',
                   'Baño de rodio',
                   'Diamantes cultivados en laboratorio, aprox. 1.5 ct en total, talla brillante',
                   'Largo de 17 cm y ancho de 2.5 mm. Broche de caja con seguro doble',
                   CUIDADO_ORO)),
            ('Pulsera de Eslabones', 'Pulseras', 'Acero 316L con baño de oro (PVD)',
             'Colección Dorada',
             '650.00', 32, False, False, True,
             ficha('Pulsera de eslabones planos con acabado dorado, de aspecto sólido y poco '
                   'peso. Se puede usar sola o apilada con otras pulseras finas.',
                   'Acero inoxidable 316L',
                   'Baño de oro aplicado por PVD, un proceso que forma una capa más adherida '
                   'y duradera que el baño tradicional',
                   None,
                   'Largo de 19 cm y ancho de 5 mm. Cierre de seguridad',
                   CUIDADO_PVD)),
            ('Pulsera Soleil', 'Pulseras', 'Oro amarillo 18k', 'Colección Dorada',
             '7980.00', 5, False, True, True,
             ficha('Pulsera de cadena fina con un zafiro azul al centro rodeado de pequeños '
                   'rayos que recuerdan al sol. Es ajustable, así que queda bien en muñecas '
                   'de distinto tamaño.',
                   'Oro amarillo de 18 quilates (750)',
                   'Pulido (oro macizo, sin recubrimiento)',
                   'Zafiro azul natural de 4 mm',
                   'Largo ajustable de 16 a 19 cm',
                   CUIDADO_ORO)),
            ('Esclava Grabable', 'Pulseras', 'Plata 925', 'Regalos Especiales',
             '1390.00', 0, False, False, True,
             ficha('Esclava clásica con una placa lisa al frente, lista para grabar un '
                   'nombre, una fecha o unas iniciales. Un regalo personal que cobra valor '
                   'con el tiempo.',
                   'Plata 925',
                   'Pulido con baño de rodio',
                   None,
                   'Placa de 28 x 7 mm. Cadena de 18 cm con 2 cm de extensión',
                   CUIDADO_PLATA)),
            ('Pulsera Hilo Rojo', 'Pulseras', 'Latón con baño de oro', 'Regalos Especiales',
             '290.00', 60, False, True, True,
             ficha('Pulsera de hilo rojo con un pequeño dije dorado y nudo corredizo que se '
                   'ajusta a cualquier muñeca. Es un detalle sencillo y económico para '
                   'regalar.',
                   'Hilo de poliéster encerado y dije de latón',
                   'Dije con baño de oro de 18 quilates',
                   None,
                   'Largo ajustable de 14 a 22 cm. Dije de 8 mm',
                   CUIDADO_BANO)),

            # ---------------- ARETES ----------------
            ('Aretes Argolla Pequeños', 'Aretes', 'Plata 925 con baño de oro',
             'Colección Dorada',
             '690.00', 48, False, False, True,
             ficha('Argollas pequeñas y ligeras con cierre de clic, pensadas para usarse '
                   'todos los días. Su tamaño las hace discretas y combinan con cualquier '
                   'otra joya.',
                   'Plata 925',
                   'Baño de oro de 18 quilates',
                   None,
                   'Diámetro de 15 mm y grosor de 2 mm',
                   CUIDADO_BANO)),
            ('Aretes Broquel Perla', 'Aretes', 'Plata 925', 'Elegancia en Plata',
             '980.00', 16, False, False, True,
             ficha('Broqueles clásicos con una perla redonda de agua dulce sobre poste de '
                   'plata. Son discretos y se pueden usar de día o con un vestido de noche.',
                   'Plata 925 (poste y cierre de mariposa)',
                   'Baño de rodio',
                   'Perla cultivada de agua dulce de 7 mm',
                   'Perla de 7 mm',
                   CUIDADO_PERLA)),
            ('Aretes Céleste Aguamarina', 'Aretes', 'Plata 925', 'Elegancia en Plata',
             '1120.00', 11, True, True, True,
             ficha('Aretes colgantes con una aguamarina de talla gota que da un tono azul '
                   'claro muy fresco. Ligeros y cómodos, quedan bien con ropa de día y de '
                   'noche.',
                   'Plata 925',
                   'Baño de rodio',
                   'Aguamarina natural de talla gota, de 8 x 6 mm',
                   'Largo total de 22 mm. Poste con cierre de presión',
                   CUIDADO_PLATA)),

            # ---------------- DIJES ----------------
            ('Dije Corazón Grabable', 'Dijes', 'Plata 925', 'Regalos Especiales',
             '560.00', 28, False, False, True,
             ficha('Dije en forma de corazón con superficie lisa y el reverso libre para '
                   'grabar un nombre, una fecha o un mensaje corto. Se vende sin cadena, '
                   'para que lo combines con la que ya tienes.',
                   'Plata 925',
                   'Pulido con baño de rodio',
                   None,
                   'Corazón de 14 mm. Argolla para cadenas de hasta 3 mm',
                   CUIDADO_PLATA)),
            ('Dije Inicial Oro', 'Dijes', 'Oro amarillo 14k', 'Regalos Especiales',
             '2300.00', 0, False, False, True,
             ficha('Dije con una letra inicial en oro de 14 quilates, de trazo limpio y sin '
                   'adornos. Funciona como regalo personalizado y combina con cadenas finas. '
                   'Se vende por pieza y la cadena no está incluida.',
                   'Oro amarillo de 14 quilates (585)',
                   'Pulido (oro macizo, sin recubrimiento)',
                   None,
                   'Letra de 10 mm de alto. Argolla para cadenas de hasta 1.5 mm',
                   CUIDADO_ORO)),
        ]

        productos = []
        for (nombre, categoria, material, coleccion, precio, existencias,
             destacado, es_nuevo, activo, descripcion) in datos:
            campos = {
                'categoria': cat[categoria],
                'material': mat[material],
                'coleccion': col[coleccion] if coleccion else None,
                'descripcion': descripcion,
                'precio': Decimal(precio),
                'destacado': destacado,
                'es_nuevo': es_nuevo,
                'activo': activo,
            }
            obj, creado = Producto.objects.get_or_create(
                nombre=nombre, defaults={**campos, 'existencias': existencias},
            )
            if not creado:
                # Producto ya existente: actualiza la ficha, pero conserva sus
                # existencias actuales (las mueve el inventario).
                for campo, valor in campos.items():
                    setattr(obj, campo, valor)
                obj.save()

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

    # ------------------------------------------------------------------
    def _buscar_imagen_local(self, nombre):
        slug = slugify(nombre)
        for ext in EXTENSIONES:
            ruta = DIR_IMAGENES_PRODUCTOS / f'{slug}{ext}'
            if ruta.exists():
                return ruta
        return None

    def _asignar_imagen(self, producto, nombre):
        """
        Asigna la foto local del producto (<slug>.jpg en fixtures/imagenes_productos).
        Si el producto ya tiene imagen, solo la cambia con --reemplazar-imagenes.
        """
        if producto.imagen_principal and not self.reemplazar_imagenes:
            return

        ruta = self._buscar_imagen_local(nombre)
        if ruta is None:
            self.imagenes_faltantes += 1
            self.stdout.write(self.style.WARNING(
                f'  Falta la imagen de "{nombre}": {slugify(nombre)}.jpg'
            ))
            return

        if producto.imagen_principal:
            producto.imagen_principal.delete(save=False)
        with open(ruta, 'rb') as archivo:
            producto.imagen_principal.save(ruta.name, File(archivo), save=True)
        self.stdout.write(self.style.SUCCESS(f'  Imagen asignada: {nombre}'))

    # ------------------------------------------------------------------
    def _crear_usuario(self):
        usuario, creado = User.objects.get_or_create(
            username=USUARIO_PRUEBA,
            defaults={
                'first_name': 'Mariana',
                'last_name': 'Maldonado',
                'email': 'mariana.m.h802@gmail.com',
            },
        )
        if creado:
            usuario.set_password(PASSWORD_PRUEBA)
            usuario.save()

        # El perfil lo crea automaticamente la senal post_save del modelo Perfil.
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
    def _crear_resenas(self, usuario, productos):
        # Un usuario solo puede resenar cada producto una vez, asi que cada
        # resena va a un producto distinto. Los indices siguen el orden de la
        # lista de productos de arriba.
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