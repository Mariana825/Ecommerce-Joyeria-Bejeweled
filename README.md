# Bejeweled — E-commerce de Joyas

Plataforma web de comercio electrónico para venta de joyas, construida con
Django, con el sistema de diseño Bejeweled (lila + oro, tipografías
Gilda Display y Raleway).

## Qué incluye

### Tienda
- **Landing page** con hero, banda de garantías, categorías, joyas destacadas,
  colecciones, sección del asistente IA y beneficios.
- **Catálogo** con búsqueda, filtros (categoría, material, rango de precio,
  solo disponibles), ordenamiento y paginación.
- **Detalle de producto** con galería, atributos, productos relacionados y reseñas.
- **Colecciones** curadas, con página propia por colección.
- **Favoritos** (lista de deseos) por usuario.
- **Reseñas** con calificación de 1 a 5 estrellas (una por usuario y producto).
- **Newsletter** — captura de suscriptores desde el pie de página.

### Cuenta
- Registro, login/logout, recuperación de contraseña.
- Edición de perfil, direcciones de envío, historial de pedidos.

### Compra
- Carrito basado en sesión (funciona sin iniciar sesión).
- Checkout que valida existencias, descuenta inventario y registra el pedido
  con estado "pendiente de pago".

### Administración
- Panel de Django (`/admin/`) para gestionar usuarios, productos, categorías,
  materiales, colecciones, reseñas, favoritos, suscriptores y pedidos.

## Qué falta (a propósito, para la siguiente etapa)

- Integración con la **API de PayPal** para procesar el pago real.
- **Chatbot de ventas** con Inteligencia Artificial (la sección ya está
  diseñada en el inicio, con el botón deshabilitado).
- **Traducción automática** del contenido de la plataforma.

## Instalación

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Tienda: `http://127.0.0.1:8000/` — Admin: `http://127.0.0.1:8000/admin/`

## Estructura

```
joyeria/           configuración del proyecto
usuarios/          perfil, direcciones de envío
productos/         catálogo, colecciones, reseñas, favoritos, newsletter
carrito/           carrito en sesión (sin modelos)
pedidos/           pedidos y artículos de pedido
templates/
  partials/        header, footer, tarjeta de producto, newsletter, IA, beneficios
static/css/        style.css — sistema de diseño completo
sql/               esquema SQLite y MySQL + datos de ejemplo
```

## Sistema de diseño

Los tokens del diseño original (que usaba Tailwind) están portados a CSS plano
en `static/css/style.css`, porque el proyecto Django no tiene build de Tailwind.
Se conservan los mismos nombres de variables:

| Variable | Valor | Uso |
|---|---|---|
| `--primary` | `#8A74A8` | Lila principal, botones secundarios |
| `--lilac-deep` | `#6B5487` | Botones primarios, logo |
| `--gold` | `#C9A84C` | Precios, acentos, CTA principal |
| `--background` | `#FDFBFF` | Fondo general |
| `--foreground` | `#1E1728` | Texto |
| `--muted` | `#F3EEF8` | Fondos de sección |
| `--beige` | `#F5F0E8` | Fondo del newsletter |

Tipografías: **Gilda Display** para títulos (`.font-display`, h1–h4) y
**Raleway** para el resto, cargadas desde Google Fonts.

## Notas

- Las imágenes de ejemplo del hero y de los productos sin foto apuntan a
  Unsplash. Al subir imágenes reales desde el admin, se usan esas.
- Antes de producción: cambia `SECRET_KEY`, pon `DEBUG = False` y configura
  `ALLOWED_HOSTS`.
- Los scripts de `sql/` son para documentación y diagramas ER. En Django lo
  normal es dejar que `manage.py migrate` cree las tablas.

## Datos de prueba

```bash
python manage.py poblar_bd            # llena la base con datos de prueba
python manage.py poblar_bd --limpiar  # borra y vuelve a llenar
```

Crea 20 productos, 4 colecciones, 5 categorías, 6 materiales, 1 usuario de
prueba (`mariana` / `joyeria2026`) con 2 direcciones, 6 favoritos, 6 reseñas,
1 pedido y 3 suscriptores.

Ver **GUIA_PRUEBAS.md** para el recorrido completo de pruebas.
