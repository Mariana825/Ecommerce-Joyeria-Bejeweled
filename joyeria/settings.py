"""
Configuración del proyecto 'joyeria'.

Nota: las integraciones de IA (chatbot), traducción automática y la API de
PayPal se agregarán en una etapa posterior. Este avance cubre la base del
sistema: usuarios, catálogo/productos, carrito y pedidos.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Seguridad -------------------------------------------------------------
# IMPORTANTE: reemplazar esta clave antes de pasar a producción y moverla
# a una variable de entorno.
SECRET_KEY = 'django-insecure-CAMBIAR-ESTA-CLAVE-ANTES-DE-PRODUCCION'

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# --- Aplicaciones ------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps propias del proyecto
    'usuarios',
    'productos',
    'carrito',
    'pedidos',
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
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Autenticación -------------------------------------------------------------
LOGIN_URL = 'usuarios:login'
LOGIN_REDIRECT_URL = 'productos:catalogo'
LOGOUT_REDIRECT_URL = 'productos:catalogo'
