"""
Configuración del proyecto 'joyeria'.

Integra: usuarios, catálogo/productos, carrito, pedidos, pagos (PayPal
Sandbox), traducción automática, un chatbot de atención general con IA y
una API REST de inventario (Django REST Framework) que la propia tienda
consume al vender, servida por HTTPS con certificado (ver runsslserver en
el README). Las claves de las APIs externas se leen de variables de
entorno (ver ".env.example") y nunca se escriben aquí directamente.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga el archivo .env (si existe) para poblar las variables de entorno.
load_dotenv(BASE_DIR / '.env')

# --- Seguridad -------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-CAMBIAR-ESTA-CLAVE-ANTES-DE-PRODUCCION',
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Con runsslserver el sitio se sirve por HTTPS en desarrollo; Django exige
# declarar el origen explícitamente (con esquema) para aceptar POSTs entre
# páginas servidas por https://127.0.0.1:8000 (formularios, checkout, etc.).
CSRF_TRUSTED_ORIGINS = [
    'https://localhost:8000',
    'https://127.0.0.1:8000',
]

# --- Aplicaciones ------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceros
    'rest_framework',

    # Apps propias del proyecto
    'usuarios',
    'productos',
    'carrito',
    'pedidos',
    'pagos',
    'traduccion',
    'chatbot',
    'inventario',
    'servidor_https',  # comando `runsslserver` (HTTPS de desarrollo, ver README)
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'joyeria.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Context processor propio: expone el carrito en todas las
                # plantillas (por ejemplo, para mostrar el contador en el header)
                'carrito.context_processors.datos_carrito',
                # Expone el idioma actual (ES/EN) elegido por el visitante.
                'traduccion.context_processors.datos_idioma',
                # Expone si el chatbot está configurado (para mostrar u ocultar el widget).
                'chatbot.context_processors.datos_chatbot',
            ],
        },
    },
]

WSGI_APPLICATION = 'joyeria.wsgi.application'

# --- Base de datos -----------------------------------------------------------
# SQLite para desarrollo. Para producción se recomienda PostgreSQL.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# --- Validación de contraseñas ------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Internacionalización -----------------------------------------------------
# Nota: la traducción automática del contenido (multi-idioma para el usuario
# final) es una funcionalidad de IA pendiente. Esto solo configura el idioma
# de la interfaz de Django.
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos y multimedia ------------------------------------------
# --- Archivos estáticos y multimedia ------------------------------------------
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Autenticación -------------------------------------------------------------
LOGIN_URL = 'usuarios:login'
LOGIN_REDIRECT_URL = 'productos:catalogo'
LOGOUT_REDIRECT_URL = 'productos:catalogo'

# --- PayPal (Sandbox) --------------------------------------------------------
# Credenciales de https://developer.paypal.com/dashboard/applications/sandbox
PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')  # 'sandbox' o 'live'
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')
PAYPAL_CURRENCY = os.environ.get('PAYPAL_CURRENCY', 'USD')

PAYPAL_API_BASE = (
    'https://api-m.sandbox.paypal.com' if PAYPAL_MODE != 'live'
    else 'https://api-m.paypal.com'
)

# Si no hay credenciales configuradas, el botón de PayPal se oculta y se
# muestra un aviso en su lugar en vez de fallar.
PAYPAL_CONFIGURADO = bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)


# --- Traducción automática ---------------------------------------------------
# Traducción 100% local con el paquete "argostranslate" (offline, gratis, sin
# API ni clave): los modelos de traducción se descargan e instalan una sola
# vez con `python manage.py instalar_modelos_traduccion` y a partir de ahí
# cada texto se traduce en el propio servidor, sin llamar a ningún servicio
# externo. Ver traduccion/services.py.

# --- Caché ---------------------------------------------------------------
# Guarda las traducciones en disco para evitar ejecutar Argos nuevamente
# cuando ya existe una traducción.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / 'cache',
        'TIMEOUT': 60 * 60 * 24 * 30,
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
        },
    },
}
TRADUCCION_DIRECCIONES = [('es', 'en'), ('en', 'es')]

# Cuánto tiempo (segundos) se guarda cada texto traducido en caché antes de
# volver a traducirlo. 30 días por defecto: el contenido de la tienda no
# cambia de un día a otro. (La traducción es local, pero seguimos usando
# caché porque correr el modelo neuronal en cada visita sí tiene costo de
# CPU).
TRADUCCION_CACHE_SEGUNDOS = 60 * 60 * 24 * 30

# Idiomas que el visitante puede elegir desde el selector del header.
IDIOMAS_DISPONIBLES = [('es', 'Español'), ('en', 'English')]
IDIOMA_POR_DEFECTO = 'es'


# --- Chatbot de ventas (IA) ---------------------------------------------------
# API de Gemini (Google). Consigue tu clave gratis en https://aistudio.google.com/apikey
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
CHATBOT_MODEL = os.environ.get('CHATBOT_MODEL', 'gemini-3.8-flash')
CHATBOT_CONFIGURADO = bool(GEMINI_API_KEY)

# Cuántos mensajes recientes de la conversación se reenvían como contexto
# (evita que la sesión crezca sin límite y controla el costo por mensaje).
CHATBOT_HISTORIAL_MAXIMO = 12


# --- API de inventario (Django REST Framework) --------------------------------
REST_FRAMEWORK = {
    # Sin autenticación de usuario: esta API la consumen sistemas (la propia
    # tienda, y en el futuro otros clientes), no personas con sesión iniciada.
    # El acceso se controla con la API key (ver inventario.permissions).
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',  # útil para probar en el navegador
    ],
}

# Clave compartida que deben mandar los clientes de la API en el encabezado
# 'X-API-Key'. Trae un valor de desarrollo por defecto (igual que
# DJANGO_SECRET_KEY) para que el checkout funcione sin configurar nada;
# cámbiala en el .env antes de producción. Si se deja vacía a propósito
# (INVENTARIO_API_KEY=""), la API se cierra por completo en vez de quedar
# abierta por accidente (ver inventario.permissions.TieneAPIKey).
INVENTARIO_API_KEY = os.environ.get(
    'INVENTARIO_API_KEY',
    'clave-interna-de-desarrollo-CAMBIAR-EN-PRODUCCION',
)

# URL base que usa la propia tienda para llamar a su API de inventario
# (ver inventario/cliente.py, usado desde pedidos/views.py en el checkout).
# Por defecto apunta al servidor HTTPS local de desarrollo.
API_BASE_URL = os.environ.get('API_BASE_URL', 'https://127.0.0.1:8000')

# El certificado de desarrollo (runsslserver) es autofirmado, así que por
# defecto no se verifica la cadena al llamar a la API desde dentro de la
# misma app. Con un certificado real (firmado por una autoridad reconocida)
# en producción, cambia esto a 'True' en el .env.
INVENTARIO_VERIFICAR_SSL = os.environ.get('INVENTARIO_VERIFICAR_SSL', 'False') == 'True'


# --- HTTPS ---------------------------------------------------------------------
# El servidor de desarrollo se levanta con `python manage.py runsslserver`
# (comando propio de la app "servidor_https", ver esa carpeta), que sirve el
# sitio por HTTPS con un certificado autofirmado (generado automáticamente
# la primera vez). Estas banderas de "forzar HTTPS" se dejan apagadas en
# DEBUG porque runsslserver ya sirve todo por HTTPS directamente; actívalas
# (o configúralas detrás de un proxy con certificado real) en producción.
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'False') == 'True'
