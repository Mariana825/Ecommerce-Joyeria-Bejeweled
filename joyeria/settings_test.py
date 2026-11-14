"""
Configuración EXCLUSIVA para pytest.

Importa todo de joyeria/settings.py y solo sobreescribe lo necesario para
que las pruebas sean rápidas, aisladas y NUNCA toquen servicios reales
(Gmail, PayPal, Gemini, API de inventario por red, caché en disco, etc.).
No modifica tu settings.py.
"""

from .settings import *  # noqa: F401,F403

# --- Base de datos en memoria (no toca db.sqlite3) -----------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# --- Caché en memoria (en vez de la carpeta cache/ en disco) -------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'pruebas-bejeweled',
    }
}

# --- Correo: nunca SMTP real ----------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEFAULT_FROM_EMAIL = 'bejeweled@pruebas.local'
SITE_URL = 'https://testserver'

# --- Contraseñas: hasher rápido (TU-03 vuelve a activar PBKDF2 explícitamente) ---
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# --- Integraciones externas: valores falsos (aunque tu .env tenga claves reales) --
INVENTARIO_API_KEY = 'api-key-solo-para-pruebas'
API_BASE_URL = 'https://testserver'
INVENTARIO_VERIFICAR_SSL = False

PAYPAL_MODE = 'sandbox'
PAYPAL_CLIENT_ID = 'client-id-de-prueba'
PAYPAL_CLIENT_SECRET = 'secret-de-prueba'
PAYPAL_CURRENCY = 'USD'
PAYPAL_API_BASE = 'https://api-m.sandbox.paypal.com'
PAYPAL_CONFIGURADO = True

GEMINI_API_KEY = 'clave-falsa'
CHATBOT_MODEL = 'modelo-de-prueba'
CHATBOT_CONFIGURADO = True

# Sin redirecciones forzadas a HTTPS durante las pruebas.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
