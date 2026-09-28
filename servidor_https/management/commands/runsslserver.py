"""
Comando `runsslserver`: servidor de desarrollo de Django por HTTPS.

Sustituye al paquete `django-sslserver` (abandonado): esa librería usaba
`ssl.wrap_socket()`, función que Python retiró del módulo `ssl` en
versiones recientes (de ahí el error
`AttributeError: module 'ssl' has no attribute 'wrap_socket'`, incluso con
Python 3.12). Esta versión usa la API moderna `ssl.SSLContext`, compatible
con Python 3.12+ (y versiones futuras), y se usa exactamente igual:

    python manage.py runsslserver 0.0.0.0:8000
    python manage.py runsslserver --certificate certs/cert.pem --key certs/key.pem 0.0.0.0:8000

Si no se indican --certificate/--key y no existen certs/cert.pem y
certs/key.pem, el comando genera automáticamente — con el paquete
"cryptography" — un certificado autofirmado de desarrollo, para que el
proyecto funcione por HTTPS sin ningún paso adicional (igual que antes).
"""

import datetime
import ipaddress
import ssl
from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError
from django.core.management.commands.runserver import Command as RunserverCommand
from django.core.servers.basehttp import WSGIServer

CERT_DIR = Path(settings.BASE_DIR) / 'certs'
CERT_PATH_DEFECTO = CERT_DIR / 'cert.pem'
KEY_PATH_DEFECTO = CERT_DIR / 'key.pem'


def _generar_certificado_autofirmado(cert_path, key_path):
    """Genera un certificado autofirmado de desarrollo con la librería `cryptography`."""
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError as exc:
        raise CommandError(
            'No se encontró un certificado en certs/cert.pem ni el paquete '
            '"cryptography" para generar uno automáticamente. Instala las '
            'dependencias (`pip install -r requirements.txt`) o genera un '
            'certificado con `bash certs/generar_certificado.sh`.'
        ) from exc

    llave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nombre = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, 'MX'),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, 'CDMX'),
        x509.NameAttribute(NameOID.LOCALITY_NAME, 'CDMX'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'Bejeweled'),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, 'Desarrollo'),
        x509.NameAttribute(NameOID.COMMON_NAME, 'localhost'),
    ])
    ahora = datetime.datetime.now(datetime.timezone.utc)
    certificado = (
        x509.CertificateBuilder()
        .subject_name(nombre)
        .issuer_name(nombre)
        .public_key(llave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora - datetime.timedelta(days=1))
        .not_valid_after(ahora + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName('localhost'),
                x509.IPAddress(ipaddress.ip_address('127.0.0.1')),
                x509.IPAddress(ipaddress.ip_address('0.0.0.0')),
            ]),
            critical=False,
        )
        .sign(llave, hashes.SHA256())
    )

    cert_path.parent.mkdir(parents=True, exist_ok=True)
    cert_path.write_bytes(certificado.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        llave.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def _clase_servidor_ssl(certificado, llave):
    """
    Crea una subclase de `WSGIServer` que envuelve el socket con TLS justo
    después de enlazarlo (server_bind), usando `ssl.SSLContext` — la API
    moderna que reemplaza a la función retirada `ssl.wrap_socket()`.
    """

    class ServidorWSGIConSSL(WSGIServer):
        def server_bind(self):
            super().server_bind()
            contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            contexto.load_cert_chain(certfile=str(certificado), keyfile=str(llave))
            self.socket = contexto.wrap_socket(self.socket, server_side=True)

    return ServidorWSGIConSSL


class Command(RunserverCommand):
    help = (
        'Corre el servidor de desarrollo de Django por HTTPS, con un '
        'certificado autofirmado (reemplaza a django-sslserver, '
        'incompatible con Python 3.12+).'
    )
    protocol = 'https'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--certificate', dest='certificate', default=None,
            help='Ruta al certificado (.pem). Por defecto certs/cert.pem.',
        )
        parser.add_argument(
            '--key', dest='key', default=None,
            help='Ruta a la llave privada (.pem). Por defecto certs/key.pem.',
        )

    def inner_run(self, *args, **options):
        certificado = Path(options.get('certificate') or CERT_PATH_DEFECTO)
        llave = Path(options.get('key') or KEY_PATH_DEFECTO)

        if not certificado.exists() or not llave.exists():
            self.stdout.write(
                f'No se encontró un certificado SSL; generando uno de '
                f'desarrollo autofirmado en {CERT_DIR}/ ...'
            )
            _generar_certificado_autofirmado(certificado, llave)

        # `server_cls` es el punto de extensión que usa runserver.Command
        # para elegir la clase del servidor WSGI (ver Django
        # core/management/commands/runserver.py); aquí la sustituimos por
        # nuestra versión que sirve por HTTPS.
        self.server_cls = _clase_servidor_ssl(certificado, llave)
        super().inner_run(*args, **options)
