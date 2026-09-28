#!/bin/bash
# ============================================================
#  Genera un certificado SSL autofirmado para desarrollo.
#
#  No es obligatorio correrlo: `python manage.py runsslserver` ya genera
#  automáticamente un certificado de desarrollo la primera vez que lo
#  ejecutas, y funciona sin este paso. Usa este script solo si quieres tu
#  propio certificado (por ejemplo, para que el navegador lo identifique
#  con tu nombre en vez del genérico autogenerado).
#
#  Uso:
#      cd joyeria_ecommerce
#      bash certs/generar_certificado.sh
#
#  Genera certs/cert.pem (certificado público) y certs/key.pem (llave
#  privada — NUNCA la subas a git; certs/.gitignore ya la excluye).
# ============================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$DIR/key.pem" \
    -out "$DIR/cert.pem" \
    -days 365 \
    -subj "/C=MX/ST=CDMX/L=CDMX/O=Bejeweled/OU=Desarrollo/CN=localhost"

echo ""
echo "Certificado generado:"
echo "  $DIR/cert.pem"
echo "  $DIR/key.pem"
echo ""
echo "Para usarlo:"
echo "  python manage.py runsslserver --certificate certs/cert.pem --key certs/key.pem 0.0.0.0:8000"
